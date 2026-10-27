"""Testes do comportamento que o fluxo de WhatsApp exige.

Estes são os testes que realmente importam: não é se o extrator acha
"Spring Boot", é se mandar um certificado no WhatsApp **não apaga** o resto
da vida profissional da pessoa.

Precisa de um PostgreSQL. Aponte DATABASE_URL_TESTE para um banco que possa
ser truncado, senão os testes são pulados:

    DATABASE_URL_TESTE=postgresql://postgres@localhost:5432/competencias_teste pytest
"""

from __future__ import annotations

import os

import pytest

from curriculos.dominio import Escopo, OrigemSkill
from curriculos.extracao import extrair
from curriculos.leitura import ler_arquivo
from curriculos.persistencia import aplicar_schema, ingerir
from tests import fabrica

psycopg = pytest.importorskip("psycopg")

DSN_TESTE = os.environ.get("DATABASE_URL_TESTE")

pytestmark = pytest.mark.skipif(
    not DSN_TESTE, reason="defina DATABASE_URL_TESTE para rodar os testes de banco"
)

TELEFONE = "+5511988887777"


@pytest.fixture()
def conexao():
    cx = psycopg.connect(DSN_TESTE)
    try:
        aplicar_schema(cx)
        cx.execute("truncate pessoa cascade")
        cx.commit()
        yield cx
        cx.commit()
    finally:
        cx.close()


def _ingerir(conexao, caminho, telefone=TELEFONE):
    resultado = extrair(ler_arquivo(caminho))
    return resultado, ingerir(conexao, resultado, telefone=telefone)


def _contar(conexao, tabela, id_pessoa, **filtros):
    sql = f"select count(*) from {tabela} where id_pessoa = %s and removido_em is null"
    valores: list[object] = [id_pessoa]
    for coluna, valor in filtros.items():
        sql += f" and {coluna} = %s"
        valores.append(valor)
    return conexao.execute(sql, valores).fetchone()[0]


# --------------------------------------------------------------------------


def test_curriculo_novo_cria_pessoa_e_fatos(conexao, tmp_path):
    caminho = fabrica.criar_docx(tmp_path / "cv1.docx", fabrica.CURRICULO_V1)
    resultado, ingestao = _ingerir(conexao, caminho)

    assert ingestao.id_pessoa is not None
    assert ingestao.status == "PROCESSADO"
    assert Escopo.SKILL_SC in resultado.escopos
    assert Escopo.EXPERIENCIA in resultado.escopos

    assert _contar(conexao, "experiencia", ingestao.id_pessoa) == 2
    assert _contar(conexao, "skill", ingestao.id_pessoa, origem="HEDGE") > 0
    assert _contar(conexao, "skill", ingestao.id_pessoa, origem="EVIDENCIA") > 0


def test_reenvio_do_mesmo_arquivo_e_noop(conexao, tmp_path):
    caminho = fabrica.criar_docx(tmp_path / "cv1.docx", fabrica.CURRICULO_V1)
    _, primeira = _ingerir(conexao, caminho)
    antes = _contar(conexao, "skill", primeira.id_pessoa)

    _, segunda = _ingerir(conexao, caminho)

    assert segunda.ja_processado is True
    assert segunda.id_documento == primeira.id_documento
    assert _contar(conexao, "skill", primeira.id_pessoa) == antes


def test_certificado_nao_apaga_skills_nem_vinculos(conexao, tmp_path):
    """A armadilha principal do fluxo de atualização parcial."""
    cv = fabrica.criar_docx(tmp_path / "cv1.docx", fabrica.CURRICULO_V1)
    _, ingestao = _ingerir(conexao, cv)
    id_pessoa = ingestao.id_pessoa

    skills_antes = _contar(conexao, "skill", id_pessoa)
    vinculos_antes = _contar(conexao, "experiencia", id_pessoa)
    assert skills_antes > 0 and vinculos_antes == 2

    cert = fabrica.criar_docx(tmp_path / "pmp.docx", fabrica.CERTIFICADO)
    resultado_cert, _ = _ingerir(conexao, cert)

    # o documento só declara o escopo de certificação
    assert resultado_cert.escopos == {Escopo.CERTIFICACAO}

    # e portanto nada mais foi tocado
    assert _contar(conexao, "skill", id_pessoa) == skills_antes
    assert _contar(conexao, "experiencia", id_pessoa) == vinculos_antes
    assert _contar(conexao, "certificacao", id_pessoa) == 1

    sigla = conexao.execute(
        "select sigla from certificacao where id_pessoa = %s", (id_pessoa,)
    ).fetchone()[0]
    assert sigla == "PMP"


def test_curriculo_atualizado_fecha_vinculo_sem_duplicar(conexao, tmp_path):
    """O emprego em aberto ganha data de fim; não vira um segundo vínculo."""
    v1 = fabrica.criar_docx(tmp_path / "cv1.docx", fabrica.CURRICULO_V1)
    _, ingestao = _ingerir(conexao, v1)
    id_pessoa = ingestao.id_pessoa

    aberto = conexao.execute(
        """
        select organizacao, inicio, fim, em_aberto
          from experiencia
         where id_pessoa = %s and em_aberto
        """,
        (id_pessoa,),
    ).fetchall()
    assert len(aberto) == 1
    assert aberto[0][0] == "Banco Alfa"
    assert aberto[0][2] is None

    v2 = fabrica.criar_docx(tmp_path / "cv2.docx", fabrica.CURRICULO_V2)
    _ingerir(conexao, v2)

    # 3 vínculos, não 4: o Banco Alfa foi atualizado
    assert _contar(conexao, "experiencia", id_pessoa) == 3

    linha = conexao.execute(
        """
        select fim, em_aberto
          from experiencia
         where id_pessoa = %s and organizacao_chave = %s
        """,
        (id_pessoa, "banco alfa"),
    ).fetchone()
    assert linha[0] is not None, "o vínculo deveria ter sido fechado"
    assert linha[1] is False

    # e o novo emprego entrou em aberto
    novo = conexao.execute(
        """
        select organizacao, em_aberto
          from experiencia
         where id_pessoa = %s and em_aberto
        """,
        (id_pessoa,),
    ).fetchall()
    assert len(novo) == 1
    assert "Gama" in novo[0][0]


def test_skill_nova_soma_sem_remover_antigas(conexao, tmp_path):
    v1 = fabrica.criar_docx(tmp_path / "cv1.docx", fabrica.CURRICULO_V1)
    _, ingestao = _ingerir(conexao, v1)
    id_pessoa = ingestao.id_pessoa

    antigas = {
        linha[0]
        for linha in conexao.execute(
            "select skill from skill where id_pessoa = %s and origem = 'HEDGE'",
            (id_pessoa,),
        ).fetchall()
    }
    assert "Hadoop" in antigas  # só aparece no V1

    v2 = fabrica.criar_docx(tmp_path / "cv2.docx", fabrica.CURRICULO_V2)
    _ingerir(conexao, v2)

    depois = {
        linha[0]
        for linha in conexao.execute(
            "select skill from skill where id_pessoa = %s and origem = 'HEDGE'",
            (id_pessoa,),
        ).fetchall()
    }
    # o V2 não menciona Hadoop, mas a pessoa não desaprendeu
    assert antigas <= depois
    assert "Kubernetes" in depois and "Terraform" in depois


def test_mencoes_acumulam_entre_documentos(conexao, tmp_path):
    v1 = fabrica.criar_docx(tmp_path / "cv1.docx", fabrica.CURRICULO_V1)
    _, ingestao = _ingerir(conexao, v1)
    id_pessoa = ingestao.id_pessoa

    def mencoes(skill: str) -> int:
        linha = conexao.execute(
            """
            select mencoes from skill
             where id_pessoa = %s and skill = %s and origem = 'HEDGE'
            """,
            (id_pessoa, skill),
        ).fetchone()
        return linha[0] if linha else 0

    antes = mencoes("Spring Boot")
    v2 = fabrica.criar_docx(tmp_path / "cv2.docx", fabrica.CURRICULO_V2)
    _ingerir(conexao, v2)
    assert mencoes("Spring Boot") == antes + 1


def test_conflito_de_identidade_vai_para_revisao(conexao, tmp_path):
    """Recrutador encaminhando currículos do próprio número."""
    cv1 = fabrica.criar_docx(tmp_path / "cv1.docx", fabrica.CURRICULO_V1)
    _ingerir(conexao, cv1, telefone="+5511900000001")

    outro = list(fabrica.CURRICULO_V1)
    outro[1] = "joao.pereira@exemplo.com.br"
    cv2 = fabrica.criar_docx(tmp_path / "cv_outro.docx", outro)
    _, ingestao = _ingerir(conexao, cv2, telefone="+5511900000001")

    assert ingestao.status == "REVISAO"
    assert "CONFLITO_IDENTIDADE" in ingestao.revisoes

    abertas = conexao.execute(
        "select count(*) from revisao where resolvido_em is null and motivo = %s",
        ("CONFLITO_IDENTIDADE",),
    ).fetchone()[0]
    assert abertas == 1


def test_visao_sem_evidencia_separa_afirmado_de_comprovado(conexao, tmp_path):
    cv = fabrica.criar_docx(tmp_path / "cv1.docx", fabrica.CURRICULO_V1)
    _, ingestao = _ingerir(conexao, cv)

    sem_evidencia = {
        linha[0]
        for linha in conexao.execute(
            "select skill from vw_skill_sem_evidencia where id_pessoa = %s",
            (ingestao.id_pessoa,),
        ).fetchall()
    }
    comprovadas = {
        linha[0]
        for linha in conexao.execute(
            "select skill from vw_skill_comprovada where id_pessoa = %s",
            (ingestao.id_pessoa,),
        ).fetchall()
    }

    # Spark aparece dentro do emprego ("Developed ingestion pipelines using
    # Spark"), então é comprovada e não pode estar na lista de afirmadas.
    assert "Spark" in comprovadas
    assert "Spark" not in sem_evidencia

    # Hibernate só aparece na frase de auto-avaliação
    assert "Hibernate" in sem_evidencia
