"""Objetos de domínio: o que o pipeline extrai de um documento.

Cada fato carrega a sua **chave natural** (``chave()``), que é o que permite
reprocessar um documento sem duplicar linha no banco. É o contrato entre a
extração e a persistência.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum


class Escopo(StrEnum):
    """Que tipo de informação um documento carrega.

    Serve para o merge: um documento só atualiza os escopos que ele traz.
    Se chega o PDF de um certificado, o escopo é só CERTIFICACAO — as 30
    skills e os 7 vínculos da pessoa continuam intactos.
    """

    SKILL_SC = "SKILL_SC"                  # skill afirmada sem comprovação
    SKILL_COMPROVADA = "SKILL_COMPROVADA"  # skill dentro de vínculo datado
    SKILL_MATRIZ = "SKILL_MATRIZ"          # skill da matriz "Technical Skills"
    CERTIFICACAO = "CERTIFICACAO"
    EXPERIENCIA = "EXPERIENCIA"


class TipoDocumento(StrEnum):
    CURRICULO = "CURRICULO"
    CERTIFICADO = "CERTIFICADO"
    INDEFINIDO = "INDEFINIDO"


class OrigemSkill(StrEnum):
    HEDGE = "HEDGE"          # "good knowledge of X" na zona de afirmação
    MATRIZ = "MATRIZ"        # tabela "Technical Skills: Languages | Java, SQL"
    EVIDENCIA = "EVIDENCIA"  # mencionada dentro de um emprego datado


@dataclass(slots=True)
class Identidade:
    """O que o documento diz sobre quem é a pessoa.

    Nenhum destes campos é confiável como chave: na amostra o e-mail sai em
    22 de 30 e o nome no corpo do documento é lixo com frequência (a primeira
    linha é "PROFESSIONAL SUMMARY" em um currículo, "ROLES" em outro).
    A identidade vem do canal (o número de quem enviou), não do documento.
    """

    nome: str | None = None
    email: str | None = None
    telefone: str | None = None
    cpf: str | None = None


@dataclass(slots=True)
class FatoSkill:
    skill: str
    categoria: str
    origem: OrigemSkill
    termo_indice: str | None = None
    rotulo_matriz: str | None = None
    organizacao: str | None = None
    tem_indicio_entrega: bool = False
    linha: int = 0
    texto_origem: str = ""

    def chave(self) -> tuple[str, str]:
        """(skill, origem) — a mesma skill pode existir afirmada e comprovada."""
        return (self.skill, str(self.origem))


@dataclass(slots=True)
class FatoCertificacao:
    sigla: str
    emissor: str
    categoria: str
    exige_renovacao: bool
    ano: int | None = None
    linha: int = 0
    texto_origem: str = ""

    def chave(self) -> tuple[str]:
        return (self.sigla,)


@dataclass(slots=True)
class FatoExperiencia:
    organizacao: str | None
    organizacao_chave: str | None
    cargo: str | None = None
    senioridade: str | None = None
    inicio: date | None = None
    fim: date | None = None
    em_aberto: bool = False
    meses: int | None = None
    linha: int = 0
    texto_origem: str = ""

    def chave(self) -> tuple[str | None, date | None]:
        """(organização normalizada, início).

        É esta chave que resolve o caso do emprego em aberto: o currículo
        antigo diz "Jan 2024 – Till Date" e o novo diz "Jan 2024 – Jun 2026".
        Mesma chave, então o merge atualiza o ``fim`` em vez de criar um
        segundo vínculo.
        """
        return (self.organizacao_chave, self.inicio)


@dataclass(slots=True)
class LinhaNaoResolvida:
    """Linha classificada como afirmação, mas sem skill reconhecida.

    Não é erro: parte é frase genérica sem skill nenhuma ("Ability to work
    under tight deadlines"), parte é termo fora do dicionário. É a fila de
    trabalho para ampliar o dicionário — por isso vai para o banco.
    """

    linha: int
    termo_indice: str | None
    texto: str


@dataclass(slots=True)
class ResultadoExtracao:
    arquivo: str
    hash_sha256: str
    tipo: TipoDocumento
    identidade: Identidade
    escopos: set[Escopo] = field(default_factory=set)
    anos_declarados: float | None = None
    skills: list[FatoSkill] = field(default_factory=list)
    certificacoes: list[FatoCertificacao] = field(default_factory=list)
    experiencias: list[FatoExperiencia] = field(default_factory=list)
    nao_resolvidas: list[LinhaNaoResolvida] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)

    def skills_por_origem(self, origem: OrigemSkill) -> list[FatoSkill]:
        return [s for s in self.skills if s.origem is origem]

    def afirmadas_sem_evidencia(self) -> list[FatoSkill]:
        """O cruzamento que interessa no fim: afirma e nunca mostrou onde usou.

        Skill que aparece na zona de afirmação (ou na matriz) e **não**
        aparece dentro de nenhum vínculo datado.
        """
        comprovadas = {
            s.skill for s in self.skills if s.origem is OrigemSkill.EVIDENCIA
        }
        vistas: set[str] = set()
        saida: list[FatoSkill] = []
        for fato in self.skills:
            if fato.origem is OrigemSkill.EVIDENCIA:
                continue
            if fato.skill in comprovadas or fato.skill in vistas:
                continue
            vistas.add(fato.skill)
            saida.append(fato)
        return saida

    def resumo(self) -> dict[str, int]:
        return {
            "skill_sc": len(self.skills_por_origem(OrigemSkill.HEDGE)),
            "skill_matriz": len(self.skills_por_origem(OrigemSkill.MATRIZ)),
            "skill_comprovada": len(self.skills_por_origem(OrigemSkill.EVIDENCIA)),
            "sem_evidencia": len(self.afirmadas_sem_evidencia()),
            "certificacoes": len(self.certificacoes),
            "experiencias": len(self.experiencias),
            "nao_resolvidas": len(self.nao_resolvidas),
        }
