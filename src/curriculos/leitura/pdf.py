"""Leitura de PDF com texto, e o gancho de OCR para os que não têm.

Certificado enviado no WhatsApp costuma vir em PDF. Dois casos:

- PDF gerado por software: tem camada de texto, ``pdfplumber`` lê, inclusive
  as tabelas;
- PDF que é foto escaneada: não tem texto. Aqui a função levanta
  ``SemTextoExtraivel`` e o documento vai para a fila de revisão.
"""

from __future__ import annotations

from pathlib import Path

from .docx import Documento, DocumentoInvalido, Paragrafo, Tabela

# Abaixo disso o "texto" do PDF é só ruído de extração; tratamos como escaneado.
MINIMO_CARACTERES = 40


def ler(caminho: str | Path) -> Documento:
    """Extrai parágrafos e tabelas de um PDF com camada de texto."""
    try:
        import pdfplumber
    except ImportError as erro:  # pragma: no cover
        raise DocumentoInvalido(
            'para ler PDF: pip install "curriculos[pdf]"  (ou: pip install pdfplumber)'
        ) from erro

    caminho = Path(caminho)
    blocos: list[Paragrafo | Tabela] = []

    try:
        with pdfplumber.open(caminho) as documento:
            for pagina in documento.pages:
                for tabela in pagina.extract_tables() or []:
                    linhas = [
                        [(celula or "").strip() for celula in linha]
                        for linha in tabela
                        if any(celula for celula in linha)
                    ]
                    if linhas:
                        blocos.append(Tabela(linhas=linhas, indice=len(blocos)))

                texto = pagina.extract_text() or ""
                for linha in texto.split("\n"):
                    limpa = " ".join(linha.split())
                    if limpa:
                        blocos.append(Paragrafo(texto=limpa, indice=len(blocos)))
    except Exception as erro:  # pdfplumber levanta vários tipos
        raise DocumentoInvalido(f"{caminho.name}: PDF ilegível ({erro})") from erro

    return Documento(blocos=blocos)


def precisa_ocr(documento: Documento) -> bool:
    """True quando o PDF não trouxe texto suficiente — provável escaneado."""
    return len(documento.texto.strip()) < MINIMO_CARACTERES


def ler_com_ocr(caminho: str | Path) -> Documento:  # pragma: no cover
    """GANCHO DE OCR — não implementado por decisão de escopo.

    Quando for implementar, os pontos de atenção medidos neste domínio:

    1. Certificado fotografado em ângulo e com brilho ruim derruba muito a
       precisão. O resultado tem que entrar com ``confianca`` baixa e cair na
       fila de revisão, não direto no banco.
    2. Sigla de certificação é curta e OCR troca letra fácil (CSM/C5M,
       ITIL/IT1L). Vale casar contra o dicionário de siglas com distância de
       edição 1, em vez de aceitar o texto cru.
    3. Para implementar: ``pytesseract`` + ``pdf2image`` (precisa de
       tesseract-ocr e poppler no sistema), ou uma API de visão.

    O resto do pipeline já funciona: basta devolver um ``Documento``.
    """
    raise NotImplementedError(
        "OCR não implementado. O documento foi registrado e está na fila de "
        "revisão — veja o docstring de ler_com_ocr para o caminho de implementação."
    )
