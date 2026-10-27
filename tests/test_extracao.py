"""Testes de extração. Não precisam de banco.

Cada teste aqui existe porque o caso correspondente **deu errado** em algum
momento da construção, com documento real da amostra. São regressões, não
exercícios.
"""

from __future__ import annotations

from datetime import date

import pytest

from curriculos.dicionarios import skills as dic_skills
from curriculos.dominio import Escopo, OrigemSkill, TipoDocumento
from curriculos.extracao import extrair, zonas
from curriculos.leitura import FormatoNaoSuportado, SemTextoExtraivel, ler_arquivo
from curriculos.normalizacao import normalizar, normalizar_empresa, varrer
from tests import fabrica


@pytest.fixture()
def curriculo(tmp_path):
    caminho = fabrica.criar_docx(
        tmp_path / "cv.docx",
        fabrica.CURRICULO_V1,
        tabelas=[
            [
                ["Programming Languages", "Java, Python, SQL, PL/SQL"],
                ["Big Data", "Hadoop, Spark, Kafka, Hive"],
            ]
        ],
    )
    return extrair(ler_arquivo(caminho))


# --------------------------------------------------------------------------
# dicionário e varredor
# --------------------------------------------------------------------------
def test_ngrama_mais_longo_ganha():
    """"pl sql" tem que vencer "sql", senão PL/SQL seria classificado como SQL."""
    indice = dic_skills.indice()
    achados = {a.canonico for a in varrer("Expertise in PL/SQL", indice)}
    assert "PL/SQL" in achados
    assert "SQL" not in achados


def test_spring_boot_nao_vira_spring():
    indice = dic_skills.indice()
    achados = {a.canonico for a in varrer("Good knowledge of Spring Boot", indice)}
    assert achados == {"Spring Boot"}


def test_apache_kafka_nao_vira_apache():
    """Regressão: "Apache" casava sozinho dentro de "Apache Kafka"."""
    indice = dic_skills.indice()
    achados = {a.canonico for a in varrer("Hands on Apache Kafka and Apache Storm", indice)}
    assert achados == {"Kafka", "Storm"}


def test_sinonimos_colapsam_no_canonico():
    indice = dic_skills.indice()
    por_aws = {a.canonico for a in varrer("Experienced in Amazon Web Services", indice)}
    por_sigla = {a.canonico for a in varrer("Experienced in AWS", indice)}
    assert por_aws == por_sigla == {"AWS"}


def test_plural_casa_no_singular():
    indice = dic_skills.indice()
    achados = {a.canonico for a in varrer("Proficient in creating ER Diagrams", indice)}
    assert "ER Diagram" in achados


def test_mais_e_cerquilha_sobrevivem_a_normalizacao():
    """Regressão: sem "+" e "#", C++ e C# viravam "c" e casavam com letra solta."""
    assert "c++" in normalizar("Expertise in C++")
    indice = dic_skills.indice()
    achados = {a.canonico for a in varrer("Expertise in C++ and C#", indice)}
    assert achados == {"C++", "C#"}
    # e uma letra c solta não casa com nada
    assert not varrer("the c of the matter", indice)


def test_dicionario_respeita_limite_de_ngrama():
    longos = [t for t in dic_skills.indice() if len(t.split()) > dic_skills.MAX_NGRAMA]
    assert longos == [], f"termos com mais de {dic_skills.MAX_NGRAMA} palavras: {longos}"


# --------------------------------------------------------------------------
# datas e períodos
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "texto,inicio,fim",
    [
        ("Client: X    MAR 2016 to Till Date", date(2016, 3, 1), None),
        ("Client: X    October 2016 – Current", date(2016, 10, 1), None),
        ("Client: X    Jul’17 – Present", date(2017, 7, 1), None),
        ("Client: X    Sep’15 to Till Date", date(2015, 9, 1), None),
        ("Client: X    Jan'17-Till date", date(2017, 1, 1), None),
        ("Client: X    May2015- July 2016", date(2015, 5, 1), date(2016, 7, 1)),
        ("Client: X    Aug 2008-May 2012", date(2008, 8, 1), date(2012, 5, 1)),
        ("Client: X    Jun’ 2014 – Dec’ 15", date(2014, 6, 1), date(2015, 12, 1)),
        ("Client: X    Jan. 2016 – Feb. 2017", date(2016, 1, 1), date(2017, 2, 1)),
        ("Client: X    Mar ‘03 –Dec ‘04", date(2003, 3, 1), date(2004, 12, 1)),
        ("Client: X    2016 – Current", date(2016, 1, 1), None),
    ],
)
def test_formatos_de_periodo_da_amostra(texto, inicio, fim):
    """Os 6 formatos que convivem na base real, mais variações."""
    la = zonas.analisar_linha(0, texto)
    assert la.tem_periodo, texto
    assert la.inicio and la.inicio.como_data() == inicio
    assert (la.fim.como_data() if la.fim else None) == fim


def test_linha_de_formacao_nao_e_vinculo():
    """Regressão: "Bachelor ... Aug 2008-May 2012" era lido como emprego."""
    la = zonas.analisar_linha(
        0, "Bachelor of Technology - Jawaharlal Nehru Technological University Aug 2008-May 2012"
    )
    assert la.e_educacao
    assert not la.inicio_vinculo


def test_anos_declarados_com_mais():
    """Regressão: "8+" chegava com o "+" preservado e não era lido."""
    la = zonas.analisar_linha(0, "8+ years of intensifying experience as Business Analyst")
    assert zonas.anos_declarados(la) == 8


def test_anos_declarados_decimal():
    la = zonas.analisar_linha(0, "more 9.5 years of experience in Business Analysis")
    assert zonas.anos_declarados(la) == 9.5


def test_normalizar_empresa_ignora_sufixo_societario():
    assert normalizar_empresa("Cognizant Inc.") == normalizar_empresa("Cognizant")
    assert normalizar_empresa("Acme Solutions Ltda") == "acme"


# --------------------------------------------------------------------------
# zonas
# --------------------------------------------------------------------------
def test_zona_separa_afirmacao_de_evidencia(curriculo):
    afirmadas = {f.skill for f in curriculo.skills_por_origem(OrigemSkill.HEDGE)}
    comprovadas = {f.skill for f in curriculo.skills_por_origem(OrigemSkill.EVIDENCIA)}

    # "Good knowledge of Spring Boot, Hibernate and PL/SQL" está no topo
    assert {"Spring Boot", "Hibernate", "PL/SQL"} <= afirmadas
    # "Developed ingestion pipelines using Spark and Kafka" está dentro do emprego
    assert {"Spark", "Kafka"} <= comprovadas


def test_skill_dentro_de_vinculo_recebe_a_organizacao(curriculo):
    spark = [
        f
        for f in curriculo.skills_por_origem(OrigemSkill.EVIDENCIA)
        if f.skill == "Spark"
    ]
    assert spark
    assert any(f.organizacao == "Banco Alfa" for f in spark)


def test_matriz_de_skills_e_lida_da_tabela(curriculo):
    matriz = {f.skill for f in curriculo.skills_por_origem(OrigemSkill.MATRIZ)}
    assert {"Java", "Python", "SQL", "PL/SQL", "Hadoop", "Hive"} <= matriz
    rotulos = {f.rotulo_matriz for f in curriculo.skills_por_origem(OrigemSkill.MATRIZ)}
    assert "Programming Languages" in rotulos


def test_afirmadas_sem_evidencia_exclui_as_comprovadas(curriculo):
    sem = {f.skill for f in curriculo.afirmadas_sem_evidencia()}
    assert "Hibernate" in sem          # só na frase de auto-avaliação
    assert "Spark" not in sem          # aparece dentro do emprego


def test_vinculo_em_aberto_e_detectado(curriculo):
    abertos = [e for e in curriculo.experiencias if e.em_aberto]
    assert len(abertos) == 1
    assert abertos[0].organizacao == "Banco Alfa"
    assert abertos[0].fim is None


def test_duracao_calculada(curriculo):
    fechado = [e for e in curriculo.experiencias if e.fim]
    assert fechado
    assert fechado[0].meses == 33  # Mar 2021 -> Dec 2023


def test_cargo_e_senioridade(curriculo):
    cargos = {e.cargo for e in curriculo.experiencias}
    assert "Sr. Data Engineer" in cargos
    senior = {e.senioridade for e in curriculo.experiencias}
    assert "sr" in senior


# --------------------------------------------------------------------------
# certificação
# --------------------------------------------------------------------------
def test_certificado_traz_emissor_e_ano(tmp_path):
    caminho = fabrica.criar_docx(tmp_path / "pmp.docx", fabrica.CERTIFICADO)
    resultado = extrair(ler_arquivo(caminho))
    assert resultado.escopos == {Escopo.CERTIFICACAO}
    assert resultado.tipo is TipoDocumento.CERTIFICADO
    assert len(resultado.certificacoes) == 1
    cert = resultado.certificacoes[0]
    assert cert.sigla == "PMP"
    assert cert.emissor == "PMI"
    assert cert.exige_renovacao is True
    assert cert.ano == 2026


def test_credentials_em_frase_tecnica_nao_e_certificacao(tmp_path):
    """Regressão: "Rest API Identity Credentials" virava certificação."""
    caminho = fabrica.criar_docx(
        tmp_path / "x.docx",
        [
            "Fulano",
            "PROFESSIONAL EXPERIENCE",
            "Client: Empresa    Jan 2020 - Dec 2021",
            "Responsibilities:",
            "Implemented Spring boot application with Rest API Identity Credentials.",
        ],
    )
    resultado = extrair(ler_arquivo(caminho))
    assert resultado.certificacoes == []


# --------------------------------------------------------------------------
# leitura
# --------------------------------------------------------------------------
def test_imagem_pede_ocr(tmp_path):
    caminho = tmp_path / "certificado.jpg"
    caminho.write_bytes(b"\xff\xd8\xff\xe0 fake jpeg")
    with pytest.raises(SemTextoExtraivel):
        ler_arquivo(caminho)


def test_formato_legado_tem_mensagem_util(tmp_path):
    caminho = tmp_path / "cv.doc"
    caminho.write_bytes(b"\xd0\xcf\x11\xe0")
    with pytest.raises(FormatoNaoSuportado, match="LibreOffice"):
        ler_arquivo(caminho)


def test_hash_e_estavel(tmp_path):
    a = fabrica.criar_docx(tmp_path / "a.docx", fabrica.CURRICULO_V1)
    primeiro = ler_arquivo(a).hash_sha256
    segundo = ler_arquivo(a).hash_sha256
    assert primeiro == segundo and len(primeiro) == 64
