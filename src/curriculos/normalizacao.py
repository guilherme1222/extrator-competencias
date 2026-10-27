"""Normalização de texto e varredor de n-gramas.

Uma única função de busca serve aos três campos (skill, certificação,
experiência): muda só o dicionário que ela recebe. Era a promessa de
"este modo de filtro se aplica para tudo".

Por que n-gramas e não regex: o varredor precisa do **casamento mais longo**.
Com regex, ``sql`` casaria dentro de ``pl/sql`` e ``spring`` dentro de
``spring boot``. Varrendo n-gramas de 3, 2 e 1 palavra e parando no primeiro
acerto, o termo mais específico sempre ganha.
"""

from __future__ import annotations

from dataclasses import dataclass

# "+" e "#" NÃO entram aqui: sem eles, C++ e C# viram "c" e passam a casar
# com qualquer letra c solta no texto. Foi falso positivo real.
PONTUACAO = "'’‘`\"“”-–—/\\|,;:()[]{}*•·§!?&%=<>@_~$®©™°"

_TABELA_PONTUACAO = str.maketrans({c: " " for c in PONTUACAO})
_TABELA_COM_PONTO = str.maketrans({c: " " for c in PONTUACAO + "."})

DIGITOS = frozenset("0123456789")


def normalizar(texto: str, manter_ponto: bool = False) -> str:
    """Minúsculas, pontuação virando espaço, espaços colapsados.

    ``manter_ponto=True`` preserva o ponto decimal, necessário para ler
    "9.5 years of experience". Para casar palavras, use o padrão: assim
    "experience." casa com o termo "experience".
    """
    tabela = _TABELA_PONTUACAO if manter_ponto else _TABELA_COM_PONTO
    return " ".join(texto.lower().translate(tabela).split())


def tokens(texto: str, manter_ponto: bool = False) -> list[str]:
    return normalizar(texto, manter_ponto).split()


def contem_termo(texto_normalizado: str, termo: str) -> bool:
    """Casamento de palavra inteira, sem regex."""
    return f" {termo} " in f" {texto_normalizado} "


def primeiro_termo(texto_normalizado: str, termos: tuple[str, ...] | list[str]) -> str | None:
    """Primeiro termo da lista presente no texto. A ordem da lista é a prioridade."""
    alvo = f" {texto_normalizado} "
    for termo in termos:
        if f" {termo} " in alvo:
            return termo
    return None


def termos_presentes(texto_normalizado: str, termos: tuple[str, ...] | list[str]) -> list[str]:
    alvo = f" {texto_normalizado} "
    return [termo for termo in termos if f" {termo} " in alvo]


@dataclass(frozen=True, slots=True)
class Achado:
    """Um termo do dicionário encontrado no texto."""

    canonico: str
    categoria: str
    termo_casado: str
    posicao: int


def varrer(
    texto: str,
    indice: dict[str, tuple[str, str]],
    max_ngrama: int = 3,
) -> list[Achado]:
    """Acha todos os termos do dicionário no texto, sem repetir canônico.

    ``indice`` mapeia termo de busca -> (canônico, categoria). Em cada
    posição tenta o n-grama mais longo primeiro; plural é resolvido tirando
    o "s" final quando a busca direta falha.

    Custo: ~``max_ngrama`` consultas-hash por palavra, independente do
    tamanho do dicionário.
    """
    palavras = tokens(texto)
    total = len(palavras)
    achados: list[Achado] = []
    vistos: set[str] = set()

    i = 0
    while i < total:
        casou = 0
        for k in range(min(max_ngrama, total - i), 0, -1):
            ngrama = " ".join(palavras[i : i + k])
            hit = indice.get(ngrama)
            if hit is None and len(ngrama) > 2 and ngrama.endswith("s"):
                hit = indice.get(ngrama[:-1])
            if hit is not None:
                canonico, categoria = hit
                if canonico not in vistos:
                    vistos.add(canonico)
                    achados.append(
                        Achado(
                            canonico=canonico,
                            categoria=categoria,
                            termo_casado=ngrama,
                            posicao=i,
                        )
                    )
                casou = k
                break  # n-grama mais longo ganha
        # Avança além das palavras consumidas. Sem isso, "pl sql" casava
        # PL/SQL e, na palavra seguinte, SQL de novo — e "amazon web
        # services" rendia AWS mais um "Web Services" fantasma.
        i += casou or 1

    return achados


def normalizar_empresa(nome: str) -> str:
    """Chave de comparação para nome de organização.

    Remove sufixo societário e localidade óbvia, para que "Cognizant Inc." e
    "Cognizant" casem. É a chave natural do vínculo, junto com a data de
    início — é o que evita duplicar emprego quando chega um currículo novo.
    """
    from .dicionarios.secoes import SUFIXOS_EMPRESA

    partes = normalizar(nome).split()
    uteis = [p for p in partes if p not in SUFIXOS_EMPRESA and not p.isdigit()]
    return " ".join(uteis) if uteis else normalizar(nome)
