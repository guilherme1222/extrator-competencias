"""Cabeçalhos de seção, rótulos de vínculo, meses e vocabulário de formação.

Tudo medido na amostra. Os cabeçalhos mais frequentes (ocorrências):
``responsibilities`` 116 · ``technical skills`` 20 · ``professional experience`` 19
``professional summary`` 16 · ``education`` 13 · ``web technologies`` 10
"""

from __future__ import annotations

CABEC_CERTIFICACAO: frozenset[str] = frozenset({
    "certification", "certifications", "certificate", "certificates",
    "professional certifications", "technical certifications",
    "trainings certifications", "professional trainings certifications",
    "education certifications", "certifications trainings",
    "certifications awards", "licenses", "licences",
    "professional trainings and certifications", "certificacoes",
})

CABEC_EDUCACAO: frozenset[str] = frozenset({
    "education", "educational", "academics", "academic", "academic profile",
    "educational qualification", "educational qualifications",
    "education qualification", "qualifications", "academic details",
    "formacao", "escolaridade",
})

CABEC_EXPERIENCIA: frozenset[str] = frozenset({
    "professional experience", "work experience", "experience",
    "employment history", "employment", "professional background",
    "relevant experience", "it experience", "career history",
    "projects", "project experience", "project details", "work history",
    "experiencia profissional", "experiencia",
})

CABEC_SKILLS: frozenset[str] = frozenset({
    "technical skills", "skills", "skill set", "core competencies",
    "technical skill set", "business skills", "key skills", "it skills",
    "technical expertise", "technical proficiency", "technical summary",
    "competencies", "areas of expertise", "area of expertise",
    "functional expertise", "snapshot", "technologies",
    "competencias", "habilidades",
})

CABEC_RESUMO: frozenset[str] = frozenset({
    "summary", "professional summary", "career summary", "executive summary",
    "profile", "professional profile", "objective", "career objective",
    "synopsis", "overview", "highlights", "key strengths", "about me",
    "resumo", "perfil",
})

# Rótulos que abrem uma entrada de emprego. "customer" ficou fora: casava em
# linhas de responsabilidade como "Customer Delivery & RFx...".
ROTULOS_VINCULO: tuple[str, ...] = ("client", "employer", "company", "organization")

ROTULOS_CARGO: tuple[str, ...] = ("role", "position", "designation", "title", "job title")

# Senioridade em ordem de prioridade: "Sr. Project Manager" resolve como
# "sr", não como "manager". Inverta a ordem se quiser o contrário.
SENIORIDADE: tuple[str, ...] = (
    "chief", "head", "director", "principal", "architect",
    "manager", "lead", "senior", "sr",
    "supervisor", "consultant", "specialist", "staff", "associate",
    "mid level", "junior", "jr", "intern", "trainee",
)

# Impede que "Bachelor of Technology ... Aug 2008-May 2012" seja lido como
# emprego (era o erro no Krishna_BSA).
VOCAB_EDUCACAO: tuple[str, ...] = (
    "bachelor", "bachelors", "master", "masters", "mba", "mca", "bsc", "msc",
    "b tech", "m tech", "btech", "mtech", "b e", "m e", "b s", "m s",
    "phd", "ph d", "diploma", "university", "college", "school",
    "degree", "graduation", "graduated", "intermediate", "ssc", "hsc",
)

MESES: dict[str, int] = {
    "jan": 1, "january": 1, "janeiro": 1,
    "feb": 2, "february": 2, "fev": 2, "fevereiro": 2,
    "mar": 3, "march": 3, "marco": 3,
    "apr": 4, "april": 4, "abr": 4, "abril": 4,
    "may": 5, "mai": 5, "maio": 5,
    "jun": 6, "june": 6, "junho": 6,
    "jul": 7, "july": 7, "julho": 7,
    "aug": 8, "august": 8, "ago": 8, "agosto": 8,
    "sep": 9, "sept": 9, "september": 9, "set": 9, "setembro": 9,
    "oct": 10, "october": 10, "out": 10, "outubro": 10,
    "nov": 11, "november": 11, "novembro": 11,
    "dec": 12, "december": 12, "dez": 12, "dezembro": 12,
}

# Marcadores de período em aberto (emprego atual).
FIM_ABERTO: tuple[str, ...] = (
    "present", "till date", "current", "currently", "now", "ongoing",
    "to date", "till present", "till now", "atual", "ate o momento",
)

# Sufixos societários removidos ao normalizar nome de empresa, para que
# "Cognizant Inc." e "Cognizant" casem na mesma chave natural.
SUFIXOS_EMPRESA: tuple[str, ...] = (
    "inc", "inc.", "llc", "ltd", "ltda", "limited", "corp", "corporation",
    "co", "company", "pvt", "private", "plc", "gmbh", "sa", "s a", "group",
    "technologies", "technology", "solutions", "systems", "services",
    "consulting", "consultancy", "software", "it", "sa.", "me", "eireli",
)
