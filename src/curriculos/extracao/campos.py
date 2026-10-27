"""Os três campos: skill, certificação e experiência.

Mesma mecânica para os três — varrer n-gramas contra um dicionário — mudando
só o dicionário e a condição de aceitação. O que separa um campo do outro é
a **zona** em que a linha está (ver zonas.py), não a palavra isolada.
"""

from __future__ import annotations

from ..dicionarios import certificacoes as dic_cert
from ..dicionarios import hedge, secoes
from ..dicionarios import skills as dic_skills
from ..dominio import (
    FatoCertificacao,
    FatoExperiencia,
    FatoSkill,
    LinhaNaoResolvida,
    OrigemSkill,
)
from ..leitura import Tabela
from ..normalizacao import (
    normalizar,
    normalizar_empresa,
    primeiro_termo,
    termos_presentes,
    varrer,
)
from .zonas import LinhaAnalisada, Secao, Zona, meses_entre

_IDX_SKILLS = dic_skills.indice()
_IDX_CERT = dic_cert.indice()

# Acima disto, uma linha com vocabulário de certificação é frase de
# responsabilidade, não certificado. Veio de falso positivo real:
# "Ensures all documents are completed in accordance ... certified".
MAX_TAM_CERT_FORA_DE_SECAO = 140
MAX_TAM_CERT_SIGLA = 120
MIN_TAM_SKILL_SC = 15
# Quantas linhas depois do vínculo procurar "Role:/Designation:".
JANELA_CARGO = 4


# --------------------------------------------------------------------------
# SKILL afirmada sem comprovação (zona CLAIM)
# --------------------------------------------------------------------------
def skills_afirmadas(
    analisadas: list[LinhaAnalisada],
) -> tuple[list[FatoSkill], list[LinhaNaoResolvida]]:
    """Skills na zona de afirmação, indexadas por termo de hedge.

    A varredura cobre a linha INTEIRA, não só o que vem depois do termo.
    Motivo medido: em "Hand on development experience Business Intelligence
    Reporting Tool –Teradata, ORACLE, Sybase, SQL-Server, DTS, Crystal
    Reports, MS-ACCESS, Core JAVA" o termo-índice está no começo e as 8
    tecnologias vêm antes de qualquer outro marcador. Cortar na primeira
    ocorrência do termo devolvia "experience working other web bas".
    """
    fatos: list[FatoSkill] = []
    pendentes: list[LinhaNaoResolvida] = []

    for la in analisadas:
        if la.zona is not Zona.CLAIM or la.e_lixo or la.cabecalho is not None:
            continue
        if la.tamanho <= MIN_TAM_SKILL_SC:
            continue
        termo = primeiro_termo(la.norm, hedge.TERMOS)
        if termo is None:
            continue

        tem_entrega = bool(termos_presentes(la.norm, hedge.VERBOS_ENTREGA))
        achados = varrer(la.texto, _IDX_SKILLS, dic_skills.MAX_NGRAMA)

        if not achados:
            pendentes.append(
                LinhaNaoResolvida(linha=la.indice, termo_indice=termo, texto=la.texto)
            )
            continue

        for achado in achados:
            fatos.append(
                FatoSkill(
                    skill=achado.canonico,
                    categoria=achado.categoria,
                    origem=OrigemSkill.HEDGE,
                    termo_indice=termo,
                    tem_indicio_entrega=tem_entrega,
                    linha=la.indice,
                    texto_origem=la.texto,
                )
            )

    return fatos, pendentes


# --------------------------------------------------------------------------
# SKILL comprovada (zona EVIDENCIA, dentro de um vínculo datado)
# --------------------------------------------------------------------------
def skills_comprovadas(
    analisadas: list[LinhaAnalisada],
    experiencias: list[FatoExperiencia],
) -> list[FatoSkill]:
    """Skills citadas dentro de um emprego datado, atribuídas a ele.

    Não é prova no sentido forte — ninguém auditou o currículo. Mas é
    categoricamente diferente de uma afirmação solta: aqui a pessoa amarrou
    a tecnologia a um cliente e a um período, e isso é verificável numa
    entrevista ou numa checagem de referência.
    """
    if not experiencias:
        return []

    # linha de início de cada vínculo -> organização, para atribuir contexto
    marcos = sorted(
        ((e.linha, e.organizacao) for e in experiencias if e.organizacao),
        key=lambda par: par[0],
    )

    def organizacao_em(linha: int) -> str | None:
        atual: str | None = None
        for inicio, org in marcos:
            if inicio <= linha:
                atual = org
            else:
                break
        return atual

    fatos: list[FatoSkill] = []
    for la in analisadas:
        if la.zona is not Zona.EVIDENCIA or la.e_lixo:
            continue
        if la.secao in (Secao.EDUCACAO, Secao.CERTIFICACAO):
            continue
        if la.inicio_vinculo or la.rotulo_cargo:
            continue
        for achado in varrer(la.texto, _IDX_SKILLS, dic_skills.MAX_NGRAMA):
            fatos.append(
                FatoSkill(
                    skill=achado.canonico,
                    categoria=achado.categoria,
                    origem=OrigemSkill.EVIDENCIA,
                    organizacao=organizacao_em(la.indice),
                    linha=la.indice,
                    texto_origem=la.texto,
                )
            )
    return fatos


# --------------------------------------------------------------------------
# SKILL da matriz "Technical Skills" (tabela)
# --------------------------------------------------------------------------
def skills_da_matriz(tabelas: list[Tabela]) -> list[FatoSkill]:
    """Lê a matriz de skills das tabelas: ``Languages | Java, C++, SQL``.

    Está em 26 dos 30 currículos da amostra, e é inventário declarado: a
    pessoa lista a tecnologia sem nem a frase de auto-avaliação em volta.
    Tecnicamente é a forma mais crua de skill sem comprovação.
    """
    fatos: list[FatoSkill] = []
    for tabela in tabelas:
        for rotulo, valor in tabela.pares():
            # rótulo gigante não é rótulo de matriz, é texto em tabela
            if len(rotulo) > 45 or not valor:
                continue
            for achado in varrer(valor, _IDX_SKILLS, dic_skills.MAX_NGRAMA):
                fatos.append(
                    FatoSkill(
                        skill=achado.canonico,
                        categoria=achado.categoria,
                        origem=OrigemSkill.MATRIZ,
                        rotulo_matriz=rotulo,
                        linha=tabela.indice,
                        texto_origem=f"{rotulo}: {valor}"[:400],
                    )
                )
    return fatos


# --------------------------------------------------------------------------
# CERTIFICAÇÃO
# --------------------------------------------------------------------------
def certificacoes(analisadas: list[LinhaAnalisada]) -> list[FatoCertificacao]:
    """Certificações por vocabulário + sigla, com emissor do dicionário.

    Três regras que vieram de erro medido:

    1. ``credential`` não está no vocabulário: casava em "Rest API Identity
       Credentials";
    2. sigla sozinha só vale dentro da seção de certificações e em linha
       curta, senão uma lista de ferramentas vira certificado;
    3. cabeçalho de tabela ("Certification Name", "Certified Date") e célula
       com ID numérico gigante são descartados.
    """
    fatos: list[FatoCertificacao] = []
    vistos: set[str] = set()

    for la in analisadas:
        if la.e_lixo or la.cabecalho is not None:
            continue
        if la.norm in dic_cert.LIXO:
            continue

        tem_vocab = any(primeiro_termo(la.norm, (v,)) for v in dic_cert.VOCABULARIO)
        achados = varrer(la.texto, _IDX_CERT, dic_cert.MAX_NGRAMA)

        aceita_por_vocab = tem_vocab and (
            la.secao is Secao.CERTIFICACAO
            or la.zona is Zona.CLAIM
            or la.tamanho <= MAX_TAM_CERT_FORA_DE_SECAO
        )
        aceita_por_sigla = (
            bool(achados)
            and la.secao is Secao.CERTIFICACAO
            and la.tamanho <= MAX_TAM_CERT_SIGLA
        )
        if not (aceita_por_vocab or aceita_por_sigla):
            continue

        ano = _ano_na_linha(la)

        if achados:
            for achado in achados:
                if achado.canonico in vistos:
                    continue
                vistos.add(achado.canonico)
                meta = dic_cert.metadados(achado.canonico)
                fatos.append(
                    FatoCertificacao(
                        sigla=achado.canonico,
                        emissor=meta.emissor if meta else "?",
                        categoria=meta.categoria if meta else "?",
                        exige_renovacao=meta.exige_renovacao if meta else False,
                        ano=ano,
                        linha=la.indice,
                        texto_origem=la.texto[:400],
                    )
                )
        elif aceita_por_vocab:
            # Fala de certificação mas a sigla não está no dicionário.
            # Entra com sigla "?" para cair na fila de revisão — melhor que
            # perder o fato silenciosamente.
            chave = f"?{la.indice}"
            if chave not in vistos:
                vistos.add(chave)
                fatos.append(
                    FatoCertificacao(
                        sigla="?",
                        emissor="?",
                        categoria="NAO_MAPEADA",
                        exige_renovacao=False,
                        ano=ano,
                        linha=la.indice,
                        texto_origem=la.texto[:400],
                    )
                )

    return fatos


def _ano_na_linha(la: LinhaAnalisada) -> int | None:
    for bruto in la.norm.split():
        if len(bruto) == 4 and bruto.isdigit():
            valor = int(bruto)
            if 1980 <= valor <= 2040:
                return valor
    return None


# --------------------------------------------------------------------------
# EXPERIÊNCIA
# --------------------------------------------------------------------------
def experiencias(analisadas: list[LinhaAnalisada]) -> list[FatoExperiencia]:
    """Vínculos: organização, cargo, senioridade, período e duração.

    Dois layouts convivem na base, ambos tratados:
      rótulo  (16/30): ``Client: TCF Bank    May 2017 – Till date`` + ``Role: ...``
      inline  (14/30): ``PNC Bank, Pittsburg, PA    October 2016 – Current``
    """
    por_indice = {la.indice: la for la in analisadas}
    fatos: list[FatoExperiencia] = []

    for la in analisadas:
        if la.zona is not Zona.EVIDENCIA or not la.inicio_vinculo:
            continue
        if la.secao is Secao.EDUCACAO or la.e_lixo:
            continue

        organizacao = _organizacao_da_linha(la)
        cargo = _cargo_proximo(la, por_indice, analisadas)
        senioridade = (
            primeiro_termo(normalizar(cargo), secoes.SENIORIDADE) if cargo else None
        )

        inicio, fim = la.inicio, la.fim
        # Período invertido existe: uma linha que lista "2016, 2015" rende
        # pontos fora de ordem. Em vez de gravar fim < inicio (o banco tem
        # constraint), descartamos o fim e tratamos como data única.
        if inicio and fim and fim.como_data() < inicio.como_data():
            fim = None

        meses = meses_entre(inicio, fim) if (inicio and fim) else None

        fatos.append(
            FatoExperiencia(
                organizacao=organizacao,
                organizacao_chave=normalizar_empresa(organizacao) if organizacao else None,
                cargo=cargo,
                senioridade=senioridade,
                inicio=inicio.como_data() if inicio else None,
                fim=fim.como_data() if fim else None,
                em_aberto=la.fim_aberto and fim is None,
                meses=meses,
                linha=la.indice,
                texto_origem=la.texto[:400],
            )
        )

    return fatos


def _organizacao_da_linha(la: LinhaAnalisada) -> str | None:
    """Tira a organização da linha de vínculo.

    Com rótulo: o que vem depois de "Client:". Sem rótulo: o que vem antes
    da data, cortando a cidade/estado depois da vírgula.
    """
    texto = la.texto
    if la.rotulo_vinculo and ":" in texto:
        texto = texto.split(":", 1)[1]

    # corta a partir do primeiro token que começa um período
    palavras = texto.split()
    corte = len(palavras)
    for i, bruto in enumerate(palavras):
        limpo = normalizar(bruto)
        letras = "".join(c for c in limpo if not c.isdigit())
        if letras[:3] in secoes.MESES or (limpo.isdigit() and len(limpo) == 4):
            corte = i
            break
    nome = " ".join(palavras[:corte]).strip(" ,-–—\t")

    # "PNC Bank, Pittsburg, PA" -> "PNC Bank"
    if "," in nome:
        nome = nome.split(",")[0].strip()

    nome = nome.strip(" .-–—")
    return nome or None


def _cargo_proximo(
    la: LinhaAnalisada,
    por_indice: dict[int, LinhaAnalisada],
    analisadas: list[LinhaAnalisada],
) -> str | None:
    """Procura "Role:/Position:/Designation:" nas linhas seguintes ao vínculo."""
    indices = [x.indice for x in analisadas]
    try:
        pos = indices.index(la.indice)
    except ValueError:
        return None

    for seguinte in analisadas[pos : pos + JANELA_CARGO]:
        if seguinte.rotulo_cargo:
            texto = seguinte.texto
            return texto.split(":", 1)[1].strip() if ":" in texto else texto.strip()

    # sem rótulo: a própria linha do vínculo às vezes traz o cargo
    if primeiro_termo(la.norm, secoes.SENIORIDADE):
        return la.texto.strip()
    return None
