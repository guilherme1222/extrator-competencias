"""Pipeline de extração: arquivo lido -> ResultadoExtracao."""

from __future__ import annotations

from ..dominio import (
    Escopo,
    Identidade,
    OrigemSkill,
    ResultadoExtracao,
    TipoDocumento,
)
from ..leitura import ArquivoLido
from ..normalizacao import primeiro_termo
from . import campos, zonas

__all__ = ["extrair", "campos", "zonas"]

# Com 2 vínculos ou mais, é currículo. Com nenhum e vocabulário de
# certificação em documento curto, é certificado.
MIN_VINCULOS_CURRICULO = 2
MAX_LINHAS_CERTIFICADO = 60


def _identidade(linhas: list[str]) -> Identidade:
    """E-mail do cabeçalho. Nome e telefone ficam para a camada de identidade.

    Medido na amostra: e-mail sai em 22 de 30. Não serve de chave, serve de
    sinal de conflito — se o número do WhatsApp já tem pessoa e o e-mail do
    documento é outro, isso vira item de revisão.
    """
    cabecalho = [linha for linha in linhas if linha.strip()][:18]
    prefixos = ("mailto:", "email:", "e-mail:", "@:")

    for linha in cabecalho:
        for bruto in linha.split():
            if "@" not in bruto or "." not in bruto.rsplit("@", 1)[-1]:
                continue
            limpo = bruto
            for prefixo in prefixos:
                baixo = limpo.lower()
                if prefixo in baixo:
                    limpo = limpo[baixo.index(prefixo) + len(prefixo) :]
            limpo = limpo.strip(" \"'<>()[]|,;:.·•")
            if "@" in limpo:
                return Identidade(email=limpo)

    return Identidade()


def _tipo(n_vinculos: int, n_certificacoes: int, n_linhas: int) -> TipoDocumento:
    if n_vinculos >= MIN_VINCULOS_CURRICULO:
        return TipoDocumento.CURRICULO
    if n_certificacoes and n_linhas <= MAX_LINHAS_CERTIFICADO:
        return TipoDocumento.CERTIFICADO
    return TipoDocumento.INDEFINIDO


def extrair(arquivo: ArquivoLido) -> ResultadoExtracao:
    """Roda os três campos sobre um documento já lido."""
    documento = arquivo.documento
    linhas = [p.texto for p in documento.linhas()]
    analisadas = zonas.analisar(linhas)

    experiencias = campos.experiencias(analisadas)
    afirmadas, nao_resolvidas = campos.skills_afirmadas(analisadas)
    comprovadas = campos.skills_comprovadas(analisadas, experiencias)
    matriz = campos.skills_da_matriz(documento.tabelas)
    certs = campos.certificacoes(analisadas)

    anos = next(
        (
            valor
            for valor in (zonas.anos_declarados(la) for la in analisadas)
            if valor is not None
        ),
        None,
    )

    escopos: set[Escopo] = set()
    if afirmadas:
        escopos.add(Escopo.SKILL_SC)
    if comprovadas:
        escopos.add(Escopo.SKILL_COMPROVADA)
    if matriz:
        escopos.add(Escopo.SKILL_MATRIZ)
    if certs:
        escopos.add(Escopo.CERTIFICACAO)
    if experiencias:
        escopos.add(Escopo.EXPERIENCIA)

    avisos: list[str] = []
    nao_mapeadas = [c for c in certs if c.sigla == "?"]
    if nao_mapeadas:
        avisos.append(
            f"{len(nao_mapeadas)} certificação(ões) com sigla fora do dicionário"
        )
    if not escopos:
        avisos.append("nenhum fato extraído: documento pode não ser um currículo")

    return ResultadoExtracao(
        arquivo=arquivo.caminho.name,
        hash_sha256=arquivo.hash_sha256,
        tipo=_tipo(len(experiencias), len(certs), len(linhas)),
        identidade=_identidade(linhas),
        escopos=escopos,
        anos_declarados=anos,
        skills=[*afirmadas, *matriz, *comprovadas],
        certificacoes=certs,
        experiencias=experiencias,
        nao_resolvidas=nao_resolvidas,
        avisos=avisos,
    )
