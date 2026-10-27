"""Termos-índice: o vocabulário que marca skill AFIRMADA sem comprovação.

Estes termos não são a informação. Eles são o **índice** que diz "o que vem
nesta linha é auto-avaliação, não fato comprovado". A informação é a
tecnologia que está na linha, extraída pelo varredor de skills.

Frequências medidas (ocorrências / documentos de 30):
    expertise 70/27 · well versed 52/23 · extensive 50/21
    experienced in 49/21 · good 44/19 · strong 42/22 · proficient 32/15
    hands on 29/18 · excellent 28/17 · understanding of 28/14
    knowledge of 25/13 · highly 22/15 · expert 13/11 · skilled 13/11
    exposure 12/7 · versed 10/8 · comprehensive 9/7 · familiar 6/5

Ordem = prioridade. O primeiro termo encontrado na linha é o que fica
registrado como ``termo_indice`` do fato.
"""

from __future__ import annotations

# Os mais específicos primeiro, para que "well versed" vença "versed"
# e "understanding of" vença "understanding".
TERMOS: tuple[str, ...] = (
    "understanding of",
    "knowledge of",
    "working knowledge",
    "experienced in",
    "well versed",
    "in depth",
    "hands on",
    "hand on",          # typo real, encontrado em currículo da amostra
    "comprehensive",
    "proficiency",
    "proficient",
    "knowledgeable",
    "expertise",
    "extensive",
    "exceptional",
    "outstanding",
    "familiarity",
    "familiar",
    "excellent",
    "exposure",
    "versatile",
    "thorough",
    "skillful",
    "skilled",
    "immense",
    "capable",
    "ability",
    "adept",
    "expert",
    "highly",
    "strong",
    "versed",
    "sound",
    "solid",
    "good",
    "wide",
    "great",
    "deep",
    "able",
    "experienced",
    "self motivated",
    "quick learner",
    "team player",
    "detail oriented",
    "interpersonal",
    "motivated",
    "dedicated",
    "passionate",
)

# Verbos de entrega. Não excluem a linha de SKILL_SC, mas marcam
# ``tem_indicio_entrega``: a afirmação vem junto de um fato realizado.
# São poucas as linhas que misturam os dois: ~17 de 355 na amostra.
VERBOS_ENTREGA: tuple[str, ...] = (
    "developed", "implemented", "designed", "built", "created", "delivered",
    "led", "managed", "migrated", "configured", "deployed", "automated",
    "wrote", "coded", "tested", "conducted", "performed", "analyzed",
    "coordinated", "facilitated", "maintained", "integrated", "refactored",
    "resolved", "supported", "reduced", "increased", "improved", "achieved",
    "launched", "owned", "executed", "documented", "gathered", "prepared",
)

MAX_NGRAMA = 2
