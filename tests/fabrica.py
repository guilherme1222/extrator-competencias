"""Fábrica de .docx mínimos para os testes.

Monta o pacote OOXML na mão (é um zip com 3 entradas), o que evita depender
de python-docx só para gerar fixture.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""

_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

_NS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def _paragrafo(texto: str) -> str:
    return f"<w:p><w:r><w:t xml:space=\"preserve\">{escape(texto)}</w:t></w:r></w:p>"


def _tabela(linhas: list[list[str]]) -> str:
    partes = ["<w:tbl>"]
    for linha in linhas:
        partes.append("<w:tr>")
        for celula in linha:
            partes.append(f"<w:tc>{_paragrafo(celula)}</w:tc>")
        partes.append("</w:tr>")
    partes.append("</w:tbl>")
    return "".join(partes)


def criar_docx(
    caminho: str | Path,
    paragrafos: list[str],
    tabelas: list[list[list[str]]] | None = None,
) -> Path:
    """Escreve um .docx com os parágrafos e tabelas dados (nessa ordem)."""
    caminho = Path(caminho)
    corpo = "".join(_paragrafo(p) for p in paragrafos)
    for tabela in tabelas or []:
        corpo += _tabela(tabela)

    documento = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f"<w:document {_NS}><w:body>{corpo}</w:body></w:document>"
    )

    caminho.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(caminho, "w", zipfile.ZIP_DEFLATED) as pacote:
        pacote.writestr("[Content_Types].xml", _CONTENT_TYPES)
        pacote.writestr("_rels/.rels", _RELS)
        pacote.writestr("word/document.xml", documento)
    return caminho


# --------------------------------------------------------------------------
# documentos de cenário
# --------------------------------------------------------------------------
CURRICULO_V1 = [
    "Maria Souza",
    "maria.souza@exemplo.com.br",
    "PROFESSIONAL SUMMARY",
    "8+ years of experience in software development and data engineering.",
    "Good knowledge of Spring Boot, Hibernate and PL/SQL.",
    "Expertise in Hadoop, Spark and Kafka for large scale data processing.",
    "Excellent communication and analytical skills.",
    "PROFESSIONAL EXPERIENCE",
    "Client: Banco Alfa, Sao Paulo, SP          Jan 2024 - Till Date",
    "Role: Sr. Data Engineer",
    "Responsibilities:",
    "Developed ingestion pipelines using Spark and Kafka.",
    "Implemented data quality checks with Great Expectations.",
    "Client: Varejo Beta                        Mar 2021 - Dec 2023",
    "Role: Data Engineer",
    "Responsibilities:",
    "Migrated legacy ETL from Informatica to Spark.",
]

# mesma pessoa, 6 meses depois: o emprego que estava em aberto agora fechou
# e entrou um emprego novo. Tem que ATUALIZAR o vínculo, não duplicar.
CURRICULO_V2 = [
    "Maria Souza",
    "maria.souza@exemplo.com.br",
    "PROFESSIONAL SUMMARY",
    "9 years of experience in software development and data engineering.",
    "Good knowledge of Spring Boot, Hibernate and PL/SQL.",
    "Strong expertise in Kubernetes and Terraform.",
    "PROFESSIONAL EXPERIENCE",
    "Client: Consultoria Gama                   Jul 2026 - Till Date",
    "Role: Lead Data Engineer",
    "Responsibilities:",
    "Led the migration to Kubernetes with Terraform.",
    "Client: Banco Alfa, Sao Paulo, SP          Jan 2024 - Jun 2026",
    "Role: Sr. Data Engineer",
    "Responsibilities:",
    "Developed ingestion pipelines using Spark and Kafka.",
    "Client: Varejo Beta                        Mar 2021 - Dec 2023",
    "Role: Data Engineer",
    "Responsibilities:",
    "Migrated legacy ETL from Informatica to Spark.",
]

# só o certificado: nenhuma skill, nenhum vínculo. É o documento que um
# "substitui tudo" usaria para apagar a vida inteira da pessoa.
CERTIFICADO = [
    "CERTIFICATIONS",
    "PMP: Certified Project Management Professional from PMI, 2026",
]
