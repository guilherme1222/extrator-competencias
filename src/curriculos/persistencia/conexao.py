"""Conexão com o PostgreSQL e aplicação do schema."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Iterator

if TYPE_CHECKING:  # só para anotação: não exige o driver instalado
    import psycopg

DSN_PADRAO = "postgresql://postgres@localhost:5432/competencias"

SQL_DIR = Path(__file__).resolve().parents[3] / "sql"


def dsn() -> str:
    """DSN vindo de DATABASE_URL, com queda para o padrão local."""
    return os.environ.get("DATABASE_URL", DSN_PADRAO)


@contextmanager
def conectar(url: str | None = None) -> Iterator["psycopg.Connection"]:
    """Conexão com transação: commit no fim, rollback em exceção.

    A ingestão de um documento é uma transação só. Se qualquer fato falhar,
    nada entra — é o que evita pessoa criada com fatos pela metade.

    O ``import`` fica aqui dentro de propósito: a prévia (``curriculos previa``)
    não toca no banco, e exigir o driver instalado só para olhar um currículo
    seria uma barreira sem motivo.
    """
    try:
        import psycopg
    except ImportError as erro:  # pragma: no cover
        raise ImportError(
            "este comando precisa do driver do PostgreSQL: "
            'pip install "curriculos[db]"  (ou: pip install "psycopg[binary]")'
        ) from erro

    conexao = psycopg.connect(url or dsn())
    try:
        with conexao:
            yield conexao
    finally:
        conexao.close()


def aplicar_schema(conexao: "psycopg.Connection") -> list[str]:
    """Roda os .sql de sql/ em ordem. Idempotente (tudo é IF NOT EXISTS)."""
    aplicados: list[str] = []
    for arquivo in sorted(SQL_DIR.glob("*.sql")):
        conexao.execute(arquivo.read_text(encoding="utf-8"))
        aplicados.append(arquivo.name)
    return aplicados
