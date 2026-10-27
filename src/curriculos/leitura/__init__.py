"""Entrada do pipeline: transformar um arquivo recebido em texto estruturado.

Um documento que chega pelo WhatsApp pode ser .docx, .pdf com texto, ou uma
foto de certificado. Os dois primeiros têm texto extraível; a foto não, e
nesse caso o documento vai para a fila de revisão com motivo explícito —
o gancho de OCR existe mas não está implementado (decisão do projeto).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from . import docx, pdf
from .docx import Documento, DocumentoInvalido, Paragrafo, Tabela

__all__ = [
    "Documento",
    "DocumentoInvalido",
    "Paragrafo",
    "Tabela",
    "SemTextoExtraivel",
    "FormatoNaoSuportado",
    "ArquivoLido",
    "ler_arquivo",
    "hash_arquivo",
]


class SemTextoExtraivel(Exception):
    """O arquivo é válido mas não tem texto (provável imagem/escaneado).

    Quem trata isso é a camada de ingestão: o documento é registrado e vai
    para a fila de revisão. É aqui que o OCR entraria.
    """


class FormatoNaoSuportado(Exception):
    """Extensão que o pipeline não sabe ler."""


@dataclass(slots=True)
class ArquivoLido:
    caminho: Path
    documento: Documento
    hash_sha256: str
    formato: str


def hash_arquivo(caminho: str | Path) -> str:
    """SHA-256 dos bytes do arquivo.

    É a chave de idempotência: no WhatsApp as pessoas reenviam o mesmo
    arquivo, e o reenvio tem que ser no-op.
    """
    h = hashlib.sha256()
    with open(caminho, "rb") as fh:
        for pedaco in iter(lambda: fh.read(1024 * 256), b""):
            h.update(pedaco)
    return h.hexdigest()


def ler_arquivo(caminho: str | Path) -> ArquivoLido:
    """Lê qualquer formato suportado e devolve o documento estruturado."""
    caminho = Path(caminho)
    sufixo = caminho.suffix.lower()

    if sufixo == ".docx":
        documento = docx.ler(caminho)
        formato = "docx"
    elif sufixo == ".pdf":
        documento = pdf.ler(caminho)
        formato = "pdf"
    elif sufixo in {".doc", ".rtf", ".odt"}:
        raise FormatoNaoSuportado(
            f"{caminho.name}: formato legado. Converta para .docx ou .pdf "
            "(o LibreOffice resolve: soffice --convert-to docx)"
        )
    elif sufixo in {".png", ".jpg", ".jpeg", ".heic", ".webp", ".tif", ".tiff"}:
        raise SemTextoExtraivel(f"{caminho.name}: imagem, precisa de OCR")
    else:
        raise FormatoNaoSuportado(f"{caminho.name}: extensão {sufixo!r} não suportada")

    if not documento.texto.strip():
        raise SemTextoExtraivel(f"{caminho.name}: nenhum texto extraível")

    return ArquivoLido(
        caminho=caminho,
        documento=documento,
        hash_sha256=hash_arquivo(caminho),
        formato=formato,
    )
