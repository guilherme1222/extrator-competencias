"""Persistência: conexão, schema e gravação com merge."""

from .conexao import aplicar_schema, conectar, dsn
from .repositorio import (
    MotivoRevisao,
    ResultadoIngestao,
    SkillAgregada,
    agregar_skills,
    chave_certificacao,
    chave_experiencia,
    chave_skill,
    ingerir,
    resolver_pessoa,
)

__all__ = [
    "aplicar_schema",
    "conectar",
    "dsn",
    "ingerir",
    "resolver_pessoa",
    "agregar_skills",
    "chave_skill",
    "chave_certificacao",
    "chave_experiencia",
    "SkillAgregada",
    "ResultadoIngestao",
    "MotivoRevisao",
]
