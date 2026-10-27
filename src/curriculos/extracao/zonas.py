"""Zonas e seções: onde, no documento, cada linha está.

É a ideia central do extrator, e ela não é sobre palavras, é sobre posição.
A mesma frase significa coisas diferentes dependendo de onde aparece:

    "Expertise in XML technologies"     <- topo do CV, solto     => AFIRMAÇÃO
    Client: JPMorgan Chase  MAR 2016..  <- ÂNCORA
    "Proficient with Quality Center"    <- dentro de emprego     => EVIDÊNCIA

A ÂNCORA é a primeira entrada de emprego do documento. Antes dela, zona
CLAIM; dela em diante, zona EVIDENCIA.

Por que não procurar o cabeçalho "Summary": na amostra de 30 currículos,
6 não têm cabeçalho de resumo nenhum (os bullets começam direto) e 1 chama
o resumo de "Responsibility:". Posição é mais robusta que rótulo.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from ..dicionarios import secoes
from ..normalizacao import (
    DIGITOS,
    contem_termo,
    normalizar,
    primeiro_termo,
    tokens,
)

# Linha mais longa que isto não é cabeçalho de emprego, é texto corrido.
MAX_TAM_VINCULO = 170
MAX_TAM_CABECALHO = 60


class Zona(StrEnum):
    CLAIM = "CLAIM"
    EVIDENCIA = "EVIDENCIA"


class Secao(StrEnum):
    INICIO = "INICIO"
    RESUMO = "RESUMO"
    SKILLS = "SKILLS"
    EXPERIENCIA = "EXPERIENCIA"
    CERTIFICACAO = "CERTIFICACAO"
    EDUCACAO = "EDUCACAO"


@dataclass(slots=True)
class Ponto:
    """Um ponto no tempo lido do texto: ano sempre, mês quando houver."""

    ano: int
    mes: int | None = None

    def como_data(self) -> date:
        return date(self.ano, self.mes or 1, 1)


@dataclass(slots=True)
class LinhaAnalisada:
    indice: int
    texto: str
    norm: str
    norm_num: str
    tamanho: int
    zona: Zona = Zona.CLAIM
    secao: Secao = Secao.INICIO
    e_lixo: bool = False
    e_educacao: bool = False
    tem_periodo: bool = False
    inicio: Ponto | None = None
    fim: Ponto | None = None
    fim_aberto: bool = False
    rotulo_vinculo: bool = False
    rotulo_cargo: bool = False
    inicio_vinculo: bool = False
    cabecalho: Secao | None = None


def _pontos_mes(palavras: list[str]) -> list[Ponto]:
    """Pontos mês+ano. Cobre os 6 formatos que convivem na base.

    "MAR 2016", "October 2016", "Jul’17" (-> "jul 17"), "may2015" (letras e
    dígitos colados), "Jan. 2016", "Jun’ 2014".
    """
    pontos: list[Ponto] = []
    total = len(palavras)
    for i, bruto in enumerate(palavras):
        digitos = "".join(c for c in bruto if c in DIGITOS)
        letras = "".join(c for c in bruto if c not in DIGITOS)
        mes = secoes.MESES.get(letras)
        if mes is None:
            continue
        if not digitos and i + 1 < total:
            proximo = palavras[i + 1]
            if proximo and all(c in DIGITOS for c in proximo):
                digitos = proximo
        if not digitos:
            continue
        try:
            valor = int(digitos)
        except ValueError:
            continue
        if len(digitos) == 2:
            ano = 1900 + valor if valor > 50 else 2000 + valor
        elif len(digitos) == 4 and 1970 <= valor <= 2040:
            ano = valor
        else:
            continue
        pontos.append(Ponto(ano=ano, mes=mes))
    return pontos


def _pontos_ano(palavras: list[str]) -> list[Ponto]:
    """Fallback para período só com ano: "2016 – Current", "2017 – Present"."""
    pontos: list[Ponto] = []
    for bruto in palavras:
        if len(bruto) == 4 and all(c in DIGITOS for c in bruto):
            valor = int(bruto)
            if 1970 <= valor <= 2040:
                pontos.append(Ponto(ano=valor))
    return pontos


def analisar_linha(indice: int, texto: str) -> LinhaAnalisada:
    norm = normalizar(texto)
    palavras = norm.split()
    tamanho = len(texto)

    # fragmento de célula ou ID numérico: "00 Certification",
    # "12382534290350329532385171259523495 ITIL/ITSM ..."
    com_letras = [p for p in palavras if len("".join(c for c in p if c not in DIGITOS)) >= 2]
    primeiro = palavras[0] if palavras else ""
    id_lixo = len(primeiro) >= 8 and all(c in DIGITOS for c in primeiro)
    e_lixo = len(com_letras) < 2 or id_lixo

    pm = _pontos_mes(palavras)
    pa: list[Ponto] = [] if pm else _pontos_ano(palavras)
    aberto = primeiro_termo(norm, secoes.FIM_ABERTO) is not None

    tem_periodo = (
        len(pm) >= 2
        or (len(pm) == 1 and aberto)
        or (len(pa) >= 2 and tamanho <= 120)
        or (len(pa) == 1 and aberto and tamanho <= 120)
    )
    pontos = pm or pa
    inicio = pontos[0] if (tem_periodo and pontos) else None
    fim = pontos[-1] if (tem_periodo and len(pontos) >= 2) else None

    rotulo_vinculo = any(norm.startswith(f"{r} ") for r in secoes.ROTULOS_VINCULO)
    rotulo_cargo = any(norm.startswith(f"{r} ") for r in secoes.ROTULOS_CARGO)
    e_educacao = primeiro_termo(norm, secoes.VOCAB_EDUCACAO) is not None

    cabecalho: Secao | None = None
    if tamanho <= MAX_TAM_CABECALHO:
        nucleo = norm
        if nucleo in secoes.CABEC_CERTIFICACAO:
            cabecalho = Secao.CERTIFICACAO
        elif nucleo in secoes.CABEC_EDUCACAO:
            cabecalho = Secao.EDUCACAO
        elif nucleo in secoes.CABEC_SKILLS:
            cabecalho = Secao.SKILLS
        elif nucleo in secoes.CABEC_RESUMO:
            cabecalho = Secao.RESUMO
        elif nucleo in secoes.CABEC_EXPERIENCIA:
            cabecalho = Secao.EXPERIENCIA

    return LinhaAnalisada(
        indice=indice,
        texto=texto,
        norm=norm,
        norm_num=normalizar(texto, manter_ponto=True),
        tamanho=tamanho,
        e_lixo=e_lixo,
        e_educacao=e_educacao,
        tem_periodo=tem_periodo,
        inicio=inicio,
        fim=fim,
        fim_aberto=aberto,
        rotulo_vinculo=rotulo_vinculo,
        rotulo_cargo=rotulo_cargo,
        # vínculo = rótulo "Client:" OU período numa linha curta,
        # e nunca uma linha de formação
        inicio_vinculo=(not e_educacao)
        and (rotulo_vinculo or (tem_periodo and tamanho <= MAX_TAM_VINCULO)),
        cabecalho=cabecalho,
    )


def analisar(linhas: list[str]) -> list[LinhaAnalisada]:
    """Analisa o documento inteiro e atribui zona e seção a cada linha."""
    analisadas = [analisar_linha(i, t) for i, t in enumerate(linhas) if t.strip()]

    ancora = next(
        (la.indice for la in analisadas if la.inicio_vinculo),
        None,
    )

    secao = Secao.INICIO
    for la in analisadas:
        if la.cabecalho is not None:
            secao = la.cabecalho
        elif la.inicio_vinculo:
            secao = Secao.EXPERIENCIA
        la.secao = secao
        la.zona = (
            Zona.CLAIM
            if (ancora is None or la.indice < ancora)
            else Zona.EVIDENCIA
        )

    return analisadas


def meses_entre(inicio: Ponto, fim: Ponto) -> int:
    return (fim.ano - inicio.ano) * 12 + ((fim.mes or 1) - (inicio.mes or 1))


def anos_declarados(linha: LinhaAnalisada) -> float | None:
    """Lê "8+ years of experience", "Over 15 Years of IT experience", "9.5 years".

    Padrão presente em 29 dos 30 currículos, sempre nas primeiras linhas.
    """
    from ..dicionarios import secoes as _s  # noqa: F401  (mantém import local)

    palavras = tokens(linha.texto, manter_ponto=True)
    if not any(contem_termo(linha.norm, p) for p in ("experience", "experiences", "exp")):
        return None

    candidatos: list[float] = []
    anos = {"year", "years", "yr", "yrs"}
    for i, bruto in enumerate(palavras):
        # "+" e "#" sobrevivem à normalização (por causa de C++/C#), então
        # "8+ years" chega aqui como "8+" e precisa ser aparado.
        limpo = bruto.strip(".+#")
        if not limpo or any(c not in DIGITOS and c != "." for c in limpo):
            continue
        vizinhos = palavras[i + 1 : i + 3]
        if not any(v.strip(".") in anos for v in vizinhos):
            continue
        try:
            valor = float(limpo)
        except ValueError:
            continue
        if 0 < valor <= 50:
            candidatos.append(valor)

    return max(candidatos) if candidatos else None
