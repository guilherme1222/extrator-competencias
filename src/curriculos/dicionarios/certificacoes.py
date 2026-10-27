"""Dicionário de certificações: sigla -> canônico, emissor e categoria.

Mesma mecânica do dicionário de skills, com dois campos a mais que só fazem
sentido aqui: **emissor** (quem emite, que é o que dá valor ao certificado) e
**exige_renovacao** (PMP vence, CSM vence, ITIL Foundation não).

Frequências medidas nos 30 currículos (ocorrências/documentos):
SAFe 12/8 · QTP 11/7 · ITIL 11/3 · Green Belt 7/3 · Six Sigma 5/3 · PMP 5/4
CSM 4/3 · PRINCE2 3/1 · CSCP 2/1 · ISTQB 2/1 · PSM 1/1 · SMAC 1/1 · MCP 1/1

Só 10 dos 30 currículos têm alguma certificação.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Certificacao:
    canonico: str
    emissor: str
    categoria: str
    exige_renovacao: bool
    termos: tuple[str, ...]


# categoria: GERENCIAL, AGIL, QUALIDADE, TECNICA, NEGOCIO, SERVICO, SEGURANCA
_DEFS: list[tuple[str, str, str, bool, list[str]]] = [
    # --- gerenciamento de projetos
    ("PMP", "PMI", "GERENCIAL", True, ["project management professional"]),
    ("CAPM", "PMI", "GERENCIAL", True, []),
    ("PMI-ACP", "PMI", "AGIL", True, ["pmi acp", "agile certified practitioner"]),
    ("PMI-RMP", "PMI", "GERENCIAL", True, ["pmi rmp"]),
    ("PMI-PBA", "PMI", "NEGOCIO", True, ["pmi pba"]),
    ("PRINCE2", "Axelos", "GERENCIAL", False, ["prince 2", "prince2 practitioner", "prince2 practioner"]),
    # --- ágil
    ("CSM", "Scrum Alliance", "AGIL", True, ["certified scrum master", "scrum master certified"]),
    ("CSPO", "Scrum Alliance", "AGIL", True, ["certified scrum product owner"]),
    ("CSP", "Scrum Alliance", "AGIL", True, ["certified scrum professional"]),
    ("PSM", "Scrum.org", "AGIL", False, ["professional scrum master"]),
    ("PSPO", "Scrum.org", "AGIL", False, ["professional scrum product owner"]),
    ("SMAC", "SCRUMstudy", "AGIL", False, ["scrum master accredited"]),
    ("SFC", "SCRUMstudy", "AGIL", False, ["scrum fundamentals certified", "scrum fundamentals"]),
    ("SAFe", "Scaled Agile", "AGIL", True, ["scaled agile", "safe agilist", "safe 4", "safe 5"]),
    # --- qualidade / processo
    ("Six Sigma Green Belt", "diversos", "QUALIDADE", False,
     ["green belt", "lean six sigma green belt", "lssgb", "cssgb", "6sigma green belt"]),
    ("Six Sigma Black Belt", "diversos", "QUALIDADE", False,
     ["black belt", "lean six sigma black belt", "lssbb", "cssbb"]),
    ("Six Sigma", "diversos", "QUALIDADE", False, ["lean six sigma", "6sigma"]),
    ("ISTQB", "ISTQB", "QUALIDADE", False, ["istqb foundation", "certified tester"]),
    # --- análise de negócio
    ("CBAP", "IIBA", "NEGOCIO", True, ["certified business analysis professional"]),
    ("CCBA", "IIBA", "NEGOCIO", True, []),
    ("ECBA", "IIBA", "NEGOCIO", False, []),
    # --- serviço / operação
    ("ITIL", "Axelos", "SERVICO", False, ["itil foundation", "itil v3", "itil v4", "itil itsm"]),
    # --- cadeia de suprimentos
    ("CSCP", "APICS", "NEGOCIO", True, ["certified supply chain professional"]),
    ("CPIM", "APICS", "NEGOCIO", True, []),
    # --- técnica
    ("OCJP", "Oracle", "TECNICA", False, ["oracle certified java programmer", "scjp", "sun certified"]),
    ("OCA", "Oracle", "TECNICA", False, ["oracle certified associate"]),
    ("OCP", "Oracle", "TECNICA", False, ["oracle certified professional"]),
    ("AWS Certified", "AWS", "TECNICA", True,
     ["aws certified", "aws solutions architect", "aws developer associate"]),
    ("Azure Certified", "Microsoft", "TECNICA", True, ["azure certified", "azure fundamentals"]),
    ("MCP", "Microsoft", "TECNICA", False, ["microsoft certified professional"]),
    ("MCTS", "Microsoft", "TECNICA", False, []),
    ("MCSD", "Microsoft", "TECNICA", False, []),
    ("CCNA", "Cisco", "TECNICA", True, []),
    ("TOGAF", "The Open Group", "TECNICA", False, []),
    ("QTP/QC", "HP", "QUALIDADE", False, ["qtp qc", "quick test professional"]),
    ("Teradata Certified", "Teradata", "TECNICA", False, ["teradata certified professional"]),
    # --- segurança / auditoria
    ("CISA", "ISACA", "SEGURANCA", True, []),
    ("CISM", "ISACA", "SEGURANCA", True, []),
    ("CISSP", "ISC2", "SEGURANCA", True, []),
]

CANON: dict[str, Certificacao] = {}
for _canon, _emissor, _cat, _renova, _extra in _DEFS:
    _termos = sorted({_canon.lower(), *_extra}, key=lambda s: -len(s))
    CANON[_canon] = Certificacao(
        canonico=_canon,
        emissor=_emissor,
        categoria=_cat,
        exige_renovacao=_renova,
        termos=tuple(_termos),
    )

# Vocabulário que indica que a linha FALA de certificação. "credential" ficou
# fora de propósito: casava em "Rest API Identity Credentials".
VOCABULARIO = (
    "certified", "certification", "certifications", "certificate",
    "certificates", "accredited", "certificado", "certificacao",
)

# Cabeçalhos de tabela de certificado, que não são certificados.
LIXO = (
    "certification name", "certification no", "certification number",
    "certification date", "certification id", "certified date",
    "certificate no", "certificate number", "credentials", "credential",
)


def indice() -> dict[str, tuple[str, str]]:
    """termo -> (canônico, categoria), no formato que o varredor espera."""
    saida: dict[str, tuple[str, str]] = {}
    for cert in CANON.values():
        for termo in cert.termos:
            saida[termo] = (cert.canonico, cert.categoria)
    return saida


def metadados(canonico: str) -> Certificacao | None:
    return CANON.get(canonico)


MAX_NGRAMA = 4  # "aws solutions architect" + folga para "oracle certified java programmer"
