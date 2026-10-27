"""Gravação no banco: merge por escopo, idempotente, sem apagar nada.

As quatro regras que este módulo implementa, e por que cada uma existe:

1. **Reenvio é no-op.** O hash SHA-256 do arquivo é UNIQUE em ``documento``.
   No WhatsApp as pessoas mandam o mesmo arquivo três vezes.

2. **Merge por escopo.** O documento declara quais escopos traz, e só esses
   são tocados. Um PDF de certificado não zera as 30 skills da pessoa — que
   é exatamente o que um "substitui tudo" faria, porque o certificado não
   menciona skill nenhuma.

3. **Upsert por chave natural.** Cada fato tem ``chave_natural``, então
   reprocessar é UPDATE. Em experiência a chave é (organização, início), e é
   isso que fecha o emprego em aberto quando chega um currículo novo em vez
   de criar um vínculo duplicado.

4. **Nunca apagar.** Fato que a pessoa parou de mencionar continua lá, com o
   ``visto_em`` antigo. Gente poda currículo para caber em uma página; isso
   não quer dizer que desaprendeu. Remover é ação humana (``removido_em``).
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # só para anotação
    import psycopg

from ..dominio import (
    Escopo,
    FatoCertificacao,
    FatoExperiencia,
    FatoSkill,
    OrigemSkill,
    ResultadoExtracao,
)


class MotivoRevisao:
    SEM_TEXTO = "SEM_TEXTO"
    CONFLITO_IDENTIDADE = "CONFLITO_IDENTIDADE"
    SIGLA_NAO_MAPEADA = "SIGLA_NAO_MAPEADA"
    SEM_FATOS = "SEM_FATOS"
    FORMATO = "FORMATO"


@dataclass(slots=True)
class ResultadoIngestao:
    """O que aconteceu com um documento."""

    id_documento: int | None
    id_pessoa: int | None
    status: str
    ja_processado: bool = False
    escopos: set[Escopo] = field(default_factory=set)
    gravados: dict[str, int] = field(default_factory=dict)
    atualizados: dict[str, int] = field(default_factory=dict)
    revisoes: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        if self.ja_processado:
            return f"documento já processado (id={self.id_documento}), nada a fazer"
        partes = [f"{k}={v}" for k, v in sorted(self.gravados.items()) if v]
        escopos = ",".join(sorted(e.value for e in self.escopos)) or "nenhum"
        extra = f" revisão: {', '.join(self.revisoes)}" if self.revisoes else ""
        return (
            f"pessoa={self.id_pessoa} doc={self.id_documento} status={self.status} "
            f"escopos=[{escopos}] {' '.join(partes)}{extra}"
        )


# --------------------------------------------------------------------------
# chaves naturais
# --------------------------------------------------------------------------
def chave_skill(skill: str, origem: OrigemSkill) -> str:
    return f"{skill}|{origem}"


def chave_certificacao(fato: FatoCertificacao) -> str:
    if fato.sigla != "?":
        return fato.sigla
    # Certificação não mapeada: a chave vem do texto, senão duas
    # certificações desconhecidas da mesma pessoa colidiriam em "?".
    digest = hashlib.sha1(fato.texto_origem.encode("utf-8")).hexdigest()[:12]
    return f"?|{digest}"


def chave_experiencia(fato: FatoExperiencia) -> str:
    org = fato.organizacao_chave or "-"
    inicio = fato.inicio.isoformat() if fato.inicio else "-"
    return f"{org}|{inicio}"


# --------------------------------------------------------------------------
# agregação antes de gravar
# --------------------------------------------------------------------------
@dataclass(slots=True)
class SkillAgregada:
    skill: str
    categoria: str
    origem: OrigemSkill
    mencoes: int = 0
    termos: set[str] = field(default_factory=set)
    organizacoes: set[str] = field(default_factory=set)
    rotulos: set[str] = field(default_factory=set)
    indicio: bool = False
    exemplo: str = ""


def agregar_skills(fatos: list[FatoSkill]) -> list[SkillAgregada]:
    """Junta (skill, origem) repetidos em uma linha, contando menções.

    A extração devolve um fato por ocorrência — numa pessoa só, as linhas de
    responsabilidade rendem centenas. O banco guarda uma linha por skill.
    """
    por_chave: dict[tuple[str, OrigemSkill], SkillAgregada] = {}
    for fato in fatos:
        chave = (fato.skill, fato.origem)
        atual = por_chave.get(chave)
        if atual is None:
            atual = SkillAgregada(
                skill=fato.skill, categoria=fato.categoria, origem=fato.origem
            )
            por_chave[chave] = atual
        atual.mencoes += 1
        if fato.termo_indice:
            atual.termos.add(fato.termo_indice)
        if fato.organizacao:
            atual.organizacoes.add(fato.organizacao)
        if fato.rotulo_matriz:
            atual.rotulos.add(fato.rotulo_matriz)
        atual.indicio = atual.indicio or fato.tem_indicio_entrega
        # exemplo = a frase mais curta, que costuma ser a mais limpa
        if not atual.exemplo or len(fato.texto_origem) < len(atual.exemplo):
            atual.exemplo = fato.texto_origem[:500]
    return list(por_chave.values())


# --------------------------------------------------------------------------
# identidade
# --------------------------------------------------------------------------
def resolver_pessoa(
    conexao: "psycopg.Connection",
    telefone: str | None,
    cpf: str | None,
    email: str | None,
    nome: str | None,
    chave_externa: str | None = None,
) -> tuple[int, list[str]]:
    """Encontra ou cria a pessoa. Devolve (id_pessoa, avisos de conflito).

    Precedência: telefone (vem do canal, é o mais confiável) > CPF >
    chave externa (carga inicial da pasta) > e-mail.

    O conflito que precisa ser pego: um recrutador encaminhando currículos
    do próprio número faria todos os candidatos colapsarem em uma pessoa só.
    Quando o número já tem pessoa e o e-mail do documento é outro, isso não
    vira merge — vira item de revisão, e os fatos ficam pendurados na pessoa
    existente até alguém decidir.
    """
    avisos: list[str] = []
    if not any((telefone, cpf, chave_externa, email)):
        raise ValueError(
            "sem identificador: informe telefone (do WhatsApp), CPF, "
            "chave externa, ou garanta que o documento tenha e-mail"
        )

    achado: tuple[int, str | None] | None = None
    for coluna, valor in (
        ("telefone_e164", telefone),
        ("cpf", cpf),
        ("chave_externa", chave_externa),
        ("email", email),
    ):
        if not valor:
            continue
        linha = conexao.execute(
            f"select id_pessoa, email from pessoa where {coluna} = %s", (valor,)
        ).fetchone()
        if linha:
            achado = (linha[0], linha[1])
            break

    if achado is None:
        linha = conexao.execute(
            """
            insert into pessoa (telefone_e164, cpf, chave_externa, nome, email)
            values (%s, %s, %s, %s, %s)
            returning id_pessoa
            """,
            (telefone, cpf, chave_externa, nome, email),
        ).fetchone()
        return int(linha[0]), avisos

    id_pessoa, email_existente = achado

    if email and email_existente and email.lower() != email_existente.lower():
        avisos.append(
            f"e-mail do documento ({email}) difere do cadastrado "
            f"({email_existente}) para a pessoa {id_pessoa}"
        )

    # completa o que estiver faltando, sem sobrescrever o que já existe
    conexao.execute(
        """
        update pessoa
           set telefone_e164 = coalesce(telefone_e164, %s),
               cpf           = coalesce(cpf, %s),
               chave_externa = coalesce(chave_externa, %s),
               nome          = coalesce(nome, %s),
               email         = coalesce(email, %s),
               atualizado_em = now()
         where id_pessoa = %s
        """,
        (telefone, cpf, chave_externa, nome, email, id_pessoa),
    )
    return int(id_pessoa), avisos


# --------------------------------------------------------------------------
# ingestão
# --------------------------------------------------------------------------
def ingerir(
    conexao: "psycopg.Connection",
    resultado: ResultadoExtracao,
    formato: str = "docx",
    telefone: str | None = None,
    cpf: str | None = None,
    nome: str | None = None,
    chave_externa: str | None = None,
) -> ResultadoIngestao:
    """Grava um documento extraído, fazendo merge só dos escopos que ele traz."""

    # --- 1. idempotência
    existente = conexao.execute(
        "select id_documento, id_pessoa, status from documento where hash_sha256 = %s",
        (resultado.hash_sha256,),
    ).fetchone()
    if existente:
        return ResultadoIngestao(
            id_documento=int(existente[0]),
            id_pessoa=existente[1],
            status=existente[2],
            ja_processado=True,
        )

    # --- 2. identidade
    id_pessoa, conflitos = resolver_pessoa(
        conexao,
        telefone=telefone,
        cpf=cpf,
        email=resultado.identidade.email,
        nome=nome or resultado.identidade.nome,
        chave_externa=chave_externa,
    )

    revisoes: list[tuple[str, str]] = [
        (MotivoRevisao.CONFLITO_IDENTIDADE, detalhe) for detalhe in conflitos
    ]
    if not resultado.escopos:
        revisoes.append(
            (MotivoRevisao.SEM_FATOS, "nenhum fato extraído do documento")
        )
    nao_mapeadas = [c for c in resultado.certificacoes if c.sigla == "?"]
    if nao_mapeadas:
        revisoes.append(
            (
                MotivoRevisao.SIGLA_NAO_MAPEADA,
                "; ".join(c.texto_origem[:120] for c in nao_mapeadas[:5]),
            )
        )

    status = "REVISAO" if revisoes else "PROCESSADO"

    # --- 3. documento
    id_documento = int(
        conexao.execute(
            """
            insert into documento
                (id_pessoa, hash_sha256, nome_arquivo, formato, tipo, escopos,
                 status, motivo_revisao, processado_em)
            values (%s, %s, %s, %s, %s, %s, %s, %s, now())
            returning id_documento
            """,
            (
                id_pessoa,
                resultado.hash_sha256,
                resultado.arquivo,
                formato,
                str(resultado.tipo),
                sorted(str(e) for e in resultado.escopos),
                status,
                "; ".join(m for m, _ in revisoes) or None,
            ),
        ).fetchone()[0]
    )

    for motivo, detalhe in revisoes:
        conexao.execute(
            """
            insert into revisao (id_documento, id_pessoa, motivo, detalhe)
            values (%s, %s, %s, %s)
            """,
            (id_documento, id_pessoa, motivo, detalhe[:2000]),
        )

    gravados: dict[str, int] = defaultdict(int)
    atualizados: dict[str, int] = defaultdict(int)

    # --- 4. merge, escopo por escopo
    escopos_de_skill = {
        OrigemSkill.HEDGE: Escopo.SKILL_SC,
        OrigemSkill.MATRIZ: Escopo.SKILL_MATRIZ,
        OrigemSkill.EVIDENCIA: Escopo.SKILL_COMPROVADA,
    }
    for origem, escopo in escopos_de_skill.items():
        if escopo not in resultado.escopos:
            continue  # escopo ausente: não toca no que já existe
        agregadas = agregar_skills(
            [f for f in resultado.skills if f.origem is origem]
        )
        novas, mexidas = _gravar_skills(
            conexao, id_pessoa, id_documento, agregadas
        )
        gravados[f"skill_{origem.value.lower()}"] = novas
        atualizados[f"skill_{origem.value.lower()}"] = mexidas

    if Escopo.CERTIFICACAO in resultado.escopos:
        novas, mexidas = _gravar_certificacoes(
            conexao, id_pessoa, id_documento, resultado.certificacoes
        )
        gravados["certificacao"] = novas
        atualizados["certificacao"] = mexidas

    if Escopo.EXPERIENCIA in resultado.escopos:
        novas, mexidas = _gravar_experiencias(
            conexao, id_pessoa, id_documento, resultado.experiencias
        )
        gravados["experiencia"] = novas
        atualizados["experiencia"] = mexidas

    # --- 5. fila do dicionário
    for pendente in resultado.nao_resolvidas:
        conexao.execute(
            """
            insert into linha_nao_resolvida
                (id_pessoa, id_documento, linha, termo_indice, texto)
            values (%s, %s, %s, %s, %s)
            """,
            (
                id_pessoa,
                id_documento,
                pendente.linha,
                pendente.termo_indice,
                pendente.texto[:2000],
            ),
        )
    gravados["linha_nao_resolvida"] = len(resultado.nao_resolvidas)

    return ResultadoIngestao(
        id_documento=id_documento,
        id_pessoa=id_pessoa,
        status=status,
        escopos=set(resultado.escopos),
        gravados=dict(gravados),
        atualizados=dict(atualizados),
        revisoes=[m for m, _ in revisoes],
    )


def _contar(resultados: list[Any]) -> tuple[int, int]:
    """(novos, atualizados) a partir do flag devolvido pelo upsert.

    Truque padrão do Postgres: em ON CONFLICT DO UPDATE, ``xmax`` da linha
    devolvida é diferente de zero quando houve UPDATE, e zero no INSERT.
    A comparação é feita no SQL (``xmax = 0 as inseriu``) porque o tipo xid
    não chega como inteiro no driver.
    """
    novos = sum(1 for linha in resultados if linha and linha[1] is True)
    return novos, len(resultados) - novos


def _gravar_skills(
    conexao: "psycopg.Connection",
    id_pessoa: int,
    id_documento: int,
    agregadas: list[SkillAgregada],
) -> tuple[int, int]:
    saida: list[Any] = []
    for item in agregadas:
        linha = conexao.execute(
            """
            insert into skill
                (id_pessoa, chave_natural, skill, categoria, origem, mencoes,
                 termos_indice, organizacoes, rotulos_matriz,
                 tem_indicio_entrega, exemplo, id_documento_origem)
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            on conflict (id_pessoa, chave_natural) do update set
                mencoes = skill.mencoes + excluded.mencoes,
                termos_indice = (
                    select coalesce(array_agg(distinct t), '{}')
                      from unnest(skill.termos_indice || excluded.termos_indice) as t
                     where t is not null
                ),
                organizacoes = (
                    select coalesce(array_agg(distinct o), '{}')
                      from unnest(skill.organizacoes || excluded.organizacoes) as o
                     where o is not null
                ),
                rotulos_matriz = (
                    select coalesce(array_agg(distinct r), '{}')
                      from unnest(skill.rotulos_matriz || excluded.rotulos_matriz) as r
                     where r is not null
                ),
                tem_indicio_entrega = skill.tem_indicio_entrega or excluded.tem_indicio_entrega,
                exemplo = coalesce(skill.exemplo, excluded.exemplo),
                id_documento_origem = excluded.id_documento_origem,
                visto_em = now(),
                removido_em = null
            returning id_skill, (xmax = 0) as inseriu
            """,
            (
                id_pessoa,
                chave_skill(item.skill, item.origem),
                item.skill,
                item.categoria,
                str(item.origem),
                item.mencoes,
                sorted(item.termos),
                sorted(item.organizacoes),
                sorted(item.rotulos),
                item.indicio,
                item.exemplo or None,
                id_documento,
            ),
        ).fetchone()
        saida.append(linha)
    return _contar(saida)


def _gravar_certificacoes(
    conexao: "psycopg.Connection",
    id_pessoa: int,
    id_documento: int,
    fatos: list[FatoCertificacao],
) -> tuple[int, int]:
    saida: list[Any] = []
    for fato in fatos:
        linha = conexao.execute(
            """
            insert into certificacao
                (id_pessoa, chave_natural, sigla, emissor, categoria,
                 exige_renovacao, ano, texto_origem, id_documento_origem)
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            on conflict (id_pessoa, chave_natural) do update set
                emissor = coalesce(excluded.emissor, certificacao.emissor),
                categoria = coalesce(excluded.categoria, certificacao.categoria),
                -- ano mais recente ganha: certificado renovado traz ano novo
                ano = greatest(coalesce(excluded.ano, 0), coalesce(certificacao.ano, 0)),
                texto_origem = coalesce(certificacao.texto_origem, excluded.texto_origem),
                id_documento_origem = excluded.id_documento_origem,
                visto_em = now(),
                removido_em = null
            returning id_certificacao, (xmax = 0) as inseriu
            """,
            (
                id_pessoa,
                chave_certificacao(fato),
                fato.sigla,
                fato.emissor,
                fato.categoria,
                fato.exige_renovacao,
                fato.ano,
                fato.texto_origem[:2000],
                id_documento,
            ),
        ).fetchone()
        saida.append(linha)
    return _contar(saida)


def _gravar_experiencias(
    conexao: "psycopg.Connection",
    id_pessoa: int,
    id_documento: int,
    fatos: list[FatoExperiencia],
) -> tuple[int, int]:
    saida: list[Any] = []
    for fato in fatos:
        linha = conexao.execute(
            """
            insert into experiencia
                (id_pessoa, chave_natural, organizacao, organizacao_chave, cargo,
                 senioridade, inicio, fim, em_aberto, meses, texto_origem,
                 id_documento_origem)
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            on conflict (id_pessoa, chave_natural) do update set
                -- o emprego que estava em aberto fecha quando chega data de fim;
                -- e nunca reabre: data de fim conhecida não volta para null
                fim = coalesce(excluded.fim, experiencia.fim),
                em_aberto = case
                    when coalesce(excluded.fim, experiencia.fim) is not null then false
                    else excluded.em_aberto or experiencia.em_aberto
                end,
                cargo = coalesce(excluded.cargo, experiencia.cargo),
                senioridade = coalesce(excluded.senioridade, experiencia.senioridade),
                organizacao = coalesce(experiencia.organizacao, excluded.organizacao),
                meses = coalesce(excluded.meses, experiencia.meses),
                texto_origem = coalesce(experiencia.texto_origem, excluded.texto_origem),
                id_documento_origem = excluded.id_documento_origem,
                visto_em = now(),
                removido_em = null
            returning id_experiencia, (xmax = 0) as inseriu
            """,
            (
                id_pessoa,
                chave_experiencia(fato),
                fato.organizacao,
                fato.organizacao_chave,
                fato.cargo,
                fato.senioridade,
                fato.inicio,
                fato.fim,
                fato.em_aberto,
                fato.meses,
                fato.texto_origem[:2000],
                id_documento,
            ),
        ).fetchone()
        saida.append(linha)
    return _contar(saida)
