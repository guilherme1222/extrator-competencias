"""Leitura de .docx preservando a ordem do documento.

Diferença em relação à versão em Power Query: aqui as tabelas chegam com
estrutura (linhas e células), não achatadas em linhas soltas. Isso importa
porque, nos 30 currículos da amostra:

- a matriz "Technical Skills" está dentro de tabela em 26 deles;
- 1 currículo tem o histórico de empregos *inteiro* dentro de tabela.

A ordem do documento também importa: o algoritmo de zonas (CLAIM antes do
primeiro emprego, EVIDENCIA depois) depende de saber o que vem antes do quê.

Implementado sobre xml.etree da biblioteca padrão, sem dependência externa.
"""

from __future__ import annotations

import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

ENTRADA_DOCUMENTO = "word/document.xml"


class DocumentoInvalido(Exception):
    """O arquivo não é um .docx legível."""


@dataclass(slots=True)
class Paragrafo:
    """Um parágrafo de texto, já com espaços colapsados."""

    texto: str
    indice: int

    @property
    def vazio(self) -> bool:
        return not self.texto.strip()


@dataclass(slots=True)
class Tabela:
    """Uma tabela, como lista de linhas de células."""

    linhas: list[list[str]]
    indice: int

    @property
    def cabecalho(self) -> list[str]:
        return self.linhas[0] if self.linhas else []

    def pares(self) -> list[tuple[str, str]]:
        """Pares (rótulo, valor) para tabelas de 2 colunas.

        É o formato da matriz de skills: ``Languages | Java, C++, SQL``.
        Tabelas com outro número de colunas devolvem lista vazia — não vale
        inventar estrutura onde ela não existe.
        """
        return [
            (linha[0].strip(), linha[1].strip())
            for linha in self.linhas
            if len(linha) == 2 and linha[0].strip() and linha[1].strip()
        ]

    def como_paragrafos(self, inicio: int) -> list[Paragrafo]:
        """Achata a tabela em parágrafos, para o algoritmo de zonas.

        Uma célula por parágrafo: é assim que o currículo cujo histórico de
        empregos está em tabela volta a ser legível pelo detector de vínculos.
        """
        saida: list[Paragrafo] = []
        i = inicio
        for linha in self.linhas:
            for celula in linha:
                if celula.strip():
                    saida.append(Paragrafo(texto=celula, indice=i))
                    i += 1
        return saida


@dataclass(slots=True)
class Documento:
    """Conteúdo de um .docx em ordem de leitura."""

    blocos: list[Paragrafo | Tabela] = field(default_factory=list)

    @property
    def tabelas(self) -> list[Tabela]:
        return [b for b in self.blocos if isinstance(b, Tabela)]

    def linhas(self) -> list[Paragrafo]:
        """Tudo como parágrafos, tabelas incluídas, na ordem do documento."""
        saida: list[Paragrafo] = []
        for bloco in self.blocos:
            if isinstance(bloco, Paragrafo):
                saida.append(Paragrafo(texto=bloco.texto, indice=len(saida)))
            else:
                saida.extend(bloco.como_paragrafos(len(saida)))
        return saida

    @property
    def texto(self) -> str:
        return "\n".join(p.texto for p in self.linhas())


def _texto_de(elemento: ElementTree.Element) -> str:
    """Junta os runs de texto de um elemento, tratando tab e quebra."""
    partes: list[str] = []
    for no in elemento.iter():
        if no.tag == f"{W}t":
            partes.append(no.text or "")
        elif no.tag in (f"{W}tab", f"{W}br"):
            partes.append(" ")
    return " ".join("".join(partes).split())


def _celulas_da_linha(tr: ElementTree.Element) -> list[str]:
    return [_texto_de(tc) for tc in tr.findall(f"{W}tc")]


def ler(caminho: str | Path) -> Documento:
    """Lê um .docx e devolve parágrafos e tabelas na ordem do documento."""
    caminho = Path(caminho)
    try:
        with zipfile.ZipFile(caminho) as pacote:
            xml = pacote.read(ENTRADA_DOCUMENTO)
    except (zipfile.BadZipFile, KeyError) as erro:
        raise DocumentoInvalido(f"{caminho.name}: não é um .docx válido ({erro})") from erro

    raiz = ElementTree.fromstring(xml)
    corpo = raiz.find(f"{W}body")
    if corpo is None:
        raise DocumentoInvalido(f"{caminho.name}: sem <w:body>")

    blocos: list[Paragrafo | Tabela] = []
    for filho in corpo:
        # Só os filhos diretos do body: tabela aninhada em tabela vem junto
        # no _texto_de da célula, o que é o comportamento desejado.
        if filho.tag == f"{W}p":
            blocos.append(Paragrafo(texto=_texto_de(filho), indice=len(blocos)))
        elif filho.tag == f"{W}tbl":
            linhas = [_celulas_da_linha(tr) for tr in filho.findall(f"{W}tr")]
            blocos.append(Tabela(linhas=[l for l in linhas if l], indice=len(blocos)))

    return Documento(blocos=blocos)
