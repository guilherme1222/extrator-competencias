"""Gera um currículo sintético para experimentar o extrator.

Existe para que qualquer pessoa consiga rodar a demonstração sem precisar de
currículo real. Os dados aqui são inventados; nenhum dado pessoal de verdade
entra neste repositório.

    python exemplos/gerar_exemplo.py
    curriculos previa exemplos/exemplo_curriculo.docx --html saida.html
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""

RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

NS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'

# Currículo inventado, no formato que a base real usa: resumo no topo com
# frases de auto-avaliação, depois os vínculos com cliente, cargo e período,
# e uma matriz de skills em tabela.
PARAGRAFOS = [
    "Maria Souza",
    "maria.souza@exemplo.com.br",
    "PROFESSIONAL SUMMARY",
    "9+ years of experience in software development and data engineering.",
    "Good knowledge of Spring Boot, Hibernate and PL/SQL.",
    "Expertise in Hadoop, Spark and Kafka for large scale data processing.",
    "Strong understanding of Kubernetes, Terraform and CI/CD pipelines.",
    "Excellent communication and analytical skills.",
    "CERTIFICATIONS",
    "PMP: Certified Project Management Professional from PMI, 2026",
    "CSM: Certified Scrum Master from Scrum Alliance",
    "PROFESSIONAL EXPERIENCE",
    "Client: Banco Alfa, Sao Paulo, SP          Jan 2024 - Till Date",
    "Role: Sr. Data Engineer",
    "Responsibilities:",
    "Developed ingestion pipelines using Spark and Kafka.",
    "Implemented data quality checks and monitoring with Airflow.",
    "Designed the star schema of the analytical layer in PostgreSQL.",
    "Client: Varejo Beta                        Mar 2021 - Dec 2023",
    "Role: Data Engineer",
    "Responsibilities:",
    "Migrated legacy ETL from Informatica to Spark.",
    "Created REST services with Spring Boot consumed by the web team.",
    "Client: Consultoria Gama                   Feb 2018 - Feb 2021",
    "Role: Jr. Java Developer",
    "Responsibilities:",
    "Maintained a Java application using Hibernate and Oracle.",
]

TABELAS = [
    [
        ["Programming Languages", "Java, Python, SQL, PL/SQL, Scala"],
        ["Big Data", "Hadoop, Spark, Kafka, Hive, Airflow"],
        ["Databases", "PostgreSQL, Oracle, MongoDB"],
        ["Tools", "JIRA, Git, Jenkins, Docker, Kubernetes"],
    ]
]


def _paragrafo(texto: str) -> str:
    return f'<w:p><w:r><w:t xml:space="preserve">{escape(texto)}</w:t></w:r></w:p>'


def _tabela(linhas: list[list[str]]) -> str:
    partes = ["<w:tbl>"]
    for linha in linhas:
        partes.append("<w:tr>")
        for celula in linha:
            partes.append(f"<w:tc>{_paragrafo(celula)}</w:tc>")
        partes.append("</w:tr>")
    partes.append("</w:tbl>")
    return "".join(partes)


def gerar(destino: Path) -> Path:
    corpo = "".join(_paragrafo(p) for p in PARAGRAFOS)
    corpo += "".join(_tabela(t) for t in TABELAS)
    documento = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f"<w:document {NS}><w:body>{corpo}</w:body></w:document>"
    )
    destino.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as pacote:
        pacote.writestr("[Content_Types].xml", CONTENT_TYPES)
        pacote.writestr("_rels/.rels", RELS)
        pacote.writestr("word/document.xml", documento)
    return destino


if __name__ == "__main__":
    alvo = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "exemplo_curriculo.docx"
    caminho = gerar(alvo)
    print(f"currículo de exemplo escrito em {caminho.resolve()}")
    print(f"agora rode:  curriculos previa \"{caminho}\" --html saida.html")
