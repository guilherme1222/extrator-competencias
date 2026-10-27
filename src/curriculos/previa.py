"""Prévia: mostra as linhas que *iriam* para o banco, sem precisar de banco.

Serve para olhar um currículo e ver a saída antes de gravar — é a tela de
conferência do MVP.

Usa as mesmas funções de chave natural e de agregação que a camada de
persistência (``chave_skill``, ``agregar_skills``...). Isso é de propósito:
se a prévia tivesse a sua própria cópia da lógica, ela mostraria uma coisa e
o banco gravaria outra na primeira vez que alguém mexesse num dos dois.
"""

from __future__ import annotations

import html as _html
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Sequence

from .dominio import OrigemSkill, ResultadoExtracao
from .persistencia.repositorio import (
    agregar_skills,
    chave_certificacao,
    chave_experiencia,
    chave_skill,
)

# Quantas linhas de skill mostrar no terminal (no HTML vão todas).
LIMITE_TERMINAL = 12


@dataclass(slots=True)
class TabelaPrevia:
    """Uma tabela do banco, com as linhas que seriam gravadas."""

    nome: str
    descricao: str
    colunas: list[str]
    linhas: list[list[Any]]

    @property
    def total(self) -> int:
        return len(self.linhas)


def _data(valor: Any) -> str:
    if valor is None:
        return ""
    return str(valor)


def montar(resultado: ResultadoExtracao, telefone: str | None = None) -> list[TabelaPrevia]:
    """Constrói a prévia de todas as tabelas para um documento extraído."""
    tabelas: list[TabelaPrevia] = []
    identidade = resultado.identidade
    chave_externa = None if telefone else f"arquivo:{resultado.arquivo}"

    # ---- pessoa
    tabelas.append(
        TabelaPrevia(
            nome="pessoa",
            descricao=(
                "Uma linha por candidato. A identidade vem do canal (telefone do "
                "WhatsApp); sem telefone, a carga usa chave_externa. CPF vem nulo: "
                "não existe CPF nos currículos."
            ),
            colunas=["telefone_e164", "cpf", "chave_externa", "nome", "email"],
            linhas=[
                [
                    telefone or "",
                    "",
                    chave_externa or "",
                    identidade.nome or "",
                    identidade.email or "",
                ]
            ],
        )
    )

    # ---- documento
    tabelas.append(
        TabelaPrevia(
            nome="documento",
            descricao=(
                "O arquivo recebido. O hash é a idempotência: reenviar o mesmo "
                "arquivo não faz nada. Os escopos dizem o que este documento "
                "pode atualizar — o merge não toca em nada fora deles."
            ),
            colunas=["nome_arquivo", "hash_sha256", "tipo", "escopos", "status"],
            linhas=[
                [
                    resultado.arquivo,
                    resultado.hash_sha256[:16] + "…",
                    str(resultado.tipo),
                    ", ".join(sorted(str(e) for e in resultado.escopos)) or "-",
                    "REVISAO" if resultado.avisos else "PROCESSADO",
                ]
            ],
        )
    )

    # ---- experiencia
    tabelas.append(
        TabelaPrevia(
            nome="experiencia",
            descricao=(
                "Vínculos. A chave natural (organização normalizada + início) é o "
                "que fecha o emprego em aberto quando chega um currículo novo, em "
                "vez de duplicar a linha."
            ),
            colunas=[
                "chave_natural",
                "organizacao",
                "cargo",
                "senioridade",
                "inicio",
                "fim",
                "em_aberto",
                "meses",
            ],
            linhas=[
                [
                    chave_experiencia(e),
                    e.organizacao or "",
                    e.cargo or "",
                    e.senioridade or "",
                    _data(e.inicio),
                    _data(e.fim),
                    "sim" if e.em_aberto else "",
                    e.meses if e.meses is not None else "",
                ]
                for e in sorted(
                    resultado.experiencias,
                    key=lambda x: (x.inicio is None, x.inicio or ""),
                    reverse=True,
                )
            ],
        )
    )

    # ---- certificacao
    tabelas.append(
        TabelaPrevia(
            nome="certificacao",
            descricao=(
                "Certificações, com emissor vindo do dicionário. Sigla '?' "
                "significa que o documento fala de certificação mas a sigla não "
                "está mapeada: vai para a fila de revisão."
            ),
            colunas=["chave_natural", "sigla", "emissor", "categoria", "renova", "ano", "texto_origem"],
            linhas=[
                [
                    chave_certificacao(c),
                    c.sigla,
                    c.emissor,
                    c.categoria,
                    "sim" if c.exige_renovacao else "",
                    c.ano or "",
                    c.texto_origem[:90],
                ]
                for c in resultado.certificacoes
            ],
        )
    )

    # ---- skill, por origem
    rotulos = {
        OrigemSkill.HEDGE: (
            "skill (origem HEDGE)",
            "Afirmada numa frase de auto-avaliação, na zona anterior ao primeiro "
            "emprego. É a skill sem comprovação no sentido estrito.",
        ),
        OrigemSkill.MATRIZ: (
            "skill (origem MATRIZ)",
            "Listada na tabela 'Technical Skills'. Inventário declarado, sem nem "
            "uma frase em volta.",
        ),
        OrigemSkill.EVIDENCIA: (
            "skill (origem EVIDENCIA)",
            "Citada dentro de um emprego datado, então vem amarrada a cliente e "
            "período. É o grau mais forte de evidência.",
        ),
    }
    for origem, (nome, descricao) in rotulos.items():
        agregadas = agregar_skills(
            [f for f in resultado.skills if f.origem is origem]
        )
        agregadas.sort(key=lambda a: (-a.mencoes, a.skill))
        tabelas.append(
            TabelaPrevia(
                nome=nome,
                descricao=descricao,
                colunas=[
                    "chave_natural",
                    "skill",
                    "categoria",
                    "mencoes",
                    "termos_indice",
                    "organizacoes",
                    "rotulos_matriz",
                    "exemplo",
                ],
                linhas=[
                    [
                        chave_skill(a.skill, a.origem),
                        a.skill,
                        a.categoria,
                        a.mencoes,
                        ", ".join(sorted(a.termos)),
                        ", ".join(sorted(a.organizacoes))[:60],
                        ", ".join(sorted(a.rotulos))[:40],
                        a.exemplo[:110],
                    ]
                    for a in agregadas
                ],
            )
        )

    # ---- a visão que responde a pergunta do projeto
    sem_evidencia = resultado.afirmadas_sem_evidencia()
    sem_evidencia.sort(key=lambda f: (f.categoria, f.skill))
    tabelas.append(
        TabelaPrevia(
            nome="vw_skill_sem_evidencia",
            descricao=(
                "A visão que responde a pergunta do projeto: em que a pessoa diz "
                "ter competência sem nunca ter mostrado onde usou. É o cruzamento "
                "de HEDGE+MATRIZ contra EVIDENCIA."
            ),
            colunas=["skill", "categoria", "origem", "indexada_por", "exemplo"],
            linhas=[
                [
                    f.skill,
                    f.categoria,
                    str(f.origem),
                    f.termo_indice or f.rotulo_matriz or "",
                    f.texto_origem[:110],
                ]
                for f in sem_evidencia
            ],
        )
    )

    # ---- fila do dicionário
    tabelas.append(
        TabelaPrevia(
            nome="linha_nao_resolvida",
            descricao=(
                "Linha que virou afirmação mas não rendeu skill. Metade é frase "
                "genérica sem skill nenhuma, metade é termo fora do dicionário. "
                "É a fila de trabalho, não erro."
            ),
            colunas=["linha", "termo_indice", "texto"],
            linhas=[
                [p.linha, p.termo_indice or "", p.texto[:130]]
                for p in resultado.nao_resolvidas
            ],
        )
    )

    return tabelas


# --------------------------------------------------------------------------
# renderizadores
# --------------------------------------------------------------------------
def _larguras(colunas: Sequence[str], linhas: Sequence[Sequence[Any]], teto: int = 40) -> list[int]:
    larguras = [len(c) for c in colunas]
    for linha in linhas:
        for i, celula in enumerate(linha):
            larguras[i] = max(larguras[i], len(str(celula)))
    return [min(l, teto) for l in larguras]


def como_texto(
    resultado: ResultadoExtracao,
    tabelas: list[TabelaPrevia],
    limite: int = LIMITE_TERMINAL,
) -> str:
    """Tabelas alinhadas para o terminal do VS Code."""
    saida: list[str] = []
    resumo = resultado.resumo()
    saida.append("=" * 100)
    saida.append(f"ENTRADA   {resultado.arquivo}")
    saida.append(
        f"          tipo={resultado.tipo}  "
        f"anos_declarados={resultado.anos_declarados or '-'}  "
        f"email={resultado.identidade.email or '-'}"
    )
    saida.append(
        "SAÍDA     "
        + "  ".join(f"{k}={v}" for k, v in resumo.items())
    )
    saida.append("=" * 100)

    for tabela in tabelas:
        saida.append("")
        saida.append(f"▸ {tabela.nome}  ({tabela.total} linha(s))")
        if not tabela.linhas:
            saida.append("   (vazia — este documento não traz este escopo)")
            continue
        larguras = _larguras(tabela.colunas, tabela.linhas)
        cabecalho = "  ".join(
            c[:larguras[i]].ljust(larguras[i]) for i, c in enumerate(tabela.colunas)
        )
        saida.append("   " + cabecalho)
        saida.append("   " + "  ".join("-" * l for l in larguras))
        for linha in tabela.linhas[:limite]:
            saida.append(
                "   "
                + "  ".join(
                    str(celula)[: larguras[i]].ljust(larguras[i])
                    for i, celula in enumerate(linha)
                )
            )
        if tabela.total > limite:
            saida.append(f"   … e outras {tabela.total - limite} linha(s)")

    if resultado.avisos:
        saida.append("")
        for aviso in resultado.avisos:
            saida.append(f"[aviso] {aviso}")
    return "\n".join(saida)


def como_markdown(resultado: ResultadoExtracao, tabelas: list[TabelaPrevia]) -> str:
    """Markdown. O VS Code pré-visualiza com Ctrl+Shift+V, sem extensão."""
    linhas: list[str] = [f"# Prévia: `{resultado.arquivo}`", ""]
    resumo = resultado.resumo()
    linhas.append(f"- **tipo**: {resultado.tipo}")
    linhas.append(f"- **anos declarados**: {resultado.anos_declarados or '-'}")
    linhas.append(f"- **e-mail**: {resultado.identidade.email or '-'}")
    linhas.append(
        f"- **escopos**: {', '.join(sorted(str(e) for e in resultado.escopos)) or '-'}"
    )
    linhas.append("")
    linhas.append("| métrica | valor |")
    linhas.append("| --- | --- |")
    for chave, valor in resumo.items():
        linhas.append(f"| {chave} | {valor} |")

    def escapar(valor: Any) -> str:
        return str(valor).replace("|", "\\|").replace("\n", " ")

    for tabela in tabelas:
        linhas.append("")
        linhas.append(f"## `{tabela.nome}` — {tabela.total} linha(s)")
        linhas.append("")
        linhas.append(f"> {tabela.descricao}")
        linhas.append("")
        if not tabela.linhas:
            linhas.append("*(vazia — este documento não traz este escopo)*")
            continue
        linhas.append("| " + " | ".join(tabela.colunas) + " |")
        linhas.append("| " + " | ".join("---" for _ in tabela.colunas) + " |")
        for linha in tabela.linhas:
            linhas.append("| " + " | ".join(escapar(c) for c in linha) + " |")
    return "\n".join(linhas) + "\n"


_CSS = """
:root {
  --fundo: #ffffff; --texto: #1a1a1a; --fraco: #6b7280; --borda: #e5e7eb;
  --cabecalho: #f9fafb; --destaque: #1d4ed8; --zebra: #fcfcfd;
  --sc: #b45309; --sc-fundo: #fffbeb; --ev: #047857; --ev-fundo: #ecfdf5;
  --mz: #6d28d9; --mz-fundo: #f5f3ff;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-tema="claro"]) {
    --fundo: #0f1115; --texto: #e6e8ec; --fraco: #9aa1ab; --borda: #262a33;
    --cabecalho: #171a21; --destaque: #7aa2ff; --zebra: #13161c;
    --sc: #fbbf24; --sc-fundo: #2a2109; --ev: #34d399; --ev-fundo: #052e22;
    --mz: #c4b5fd; --mz-fundo: #1e1b33;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0; padding: 24px 16px 64px; background: var(--fundo); color: var(--texto);
  font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
.envelope { max-width: 1240px; margin: 0 auto; }
h1 { font-size: 22px; margin: 0 0 4px; letter-spacing: -0.01em; }
h1 code { font-size: 20px; }
h2 { font-size: 15px; margin: 32px 0 2px; letter-spacing: -0.005em; }
h2 .conta { color: var(--fraco); font-weight: 400; }
code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.92em; }
.sub { color: var(--fraco); margin: 0 0 20px; }
.nota { color: var(--fraco); margin: 2px 0 10px; max-width: 76ch; font-size: 13px; }
.cartoes { display: flex; flex-wrap: wrap; gap: 8px; margin: 16px 0 8px; }
.cartao {
  border: 1px solid var(--borda); border-radius: 8px; padding: 8px 12px;
  min-width: 128px; background: var(--cabecalho);
}
.cartao b { display: block; font-size: 19px; font-variant-numeric: tabular-nums; }
.cartao span { color: var(--fraco); font-size: 11px; text-transform: uppercase; letter-spacing: 0.04em; }
.cartao.sc b { color: var(--sc); } .cartao.ev b { color: var(--ev); } .cartao.mz b { color: var(--mz); }
.rolagem { overflow-x: auto; border: 1px solid var(--borda); border-radius: 8px; }
table { border-collapse: collapse; width: 100%; font-size: 12.5px; }
th, td {
  text-align: left; padding: 7px 10px; border-bottom: 1px solid var(--borda);
  vertical-align: top; white-space: nowrap;
}
th {
  background: var(--cabecalho); font-weight: 600; font-size: 11px;
  text-transform: uppercase; letter-spacing: 0.04em; color: var(--fraco);
  position: sticky; top: 0;
}
tbody tr:nth-child(even) { background: var(--zebra); }
tbody tr:last-child td { border-bottom: none; }
td.larga { white-space: normal; min-width: 280px; max-width: 520px; color: var(--fraco); }
td.chave { font-family: ui-monospace, Menlo, monospace; color: var(--destaque); }
.vazia { color: var(--fraco); padding: 14px; font-style: italic; }
.etiqueta {
  display: inline-block; padding: 1px 7px; border-radius: 99px; font-size: 11px;
  font-weight: 600; border: 1px solid transparent;
}
.etiqueta.sc { color: var(--sc); background: var(--sc-fundo); }
.etiqueta.ev { color: var(--ev); background: var(--ev-fundo); }
.etiqueta.mz { color: var(--mz); background: var(--mz-fundo); }
.aviso {
  border-left: 3px solid var(--sc); background: var(--sc-fundo); color: var(--sc);
  padding: 8px 12px; border-radius: 0 6px 6px 0; margin: 8px 0;
}
footer { color: var(--fraco); font-size: 12px; margin-top: 40px; }
@media (max-width: 640px) { body { padding: 16px; } th, td { padding: 6px 8px; } }
"""


def _etiqueta_origem(nome: str) -> str:
    if "HEDGE" in nome:
        return '<span class="etiqueta sc">sem comprovação</span>'
    if "EVIDENCIA" in nome:
        return '<span class="etiqueta ev">comprovada</span>'
    if "MATRIZ" in nome:
        return '<span class="etiqueta mz">declarada em tabela</span>'
    return ""


def como_html(resultado: ResultadoExtracao, tabelas: list[TabelaPrevia]) -> str:
    """Página única, sem dependência externa.

    Abre no navegador ou no Simple Browser do VS Code (Ctrl+Shift+P →
    "Simple Browser: Show").
    """
    resumo = resultado.resumo()
    partes: list[str] = []

    cartoes = [
        ("sem comprovação", resumo["skill_sc"], "sc"),
        ("em tabela", resumo["skill_matriz"], "mz"),
        ("comprovadas", resumo["skill_comprovada"], "ev"),
        ("sem evidência", resumo["sem_evidencia"], "sc"),
        ("certificações", resumo["certificacoes"], ""),
        ("vínculos", resumo["experiencias"], ""),
        ("na fila", resumo["nao_resolvidas"], ""),
    ]
    partes.append('<div class="cartoes">')
    for rotulo, valor, classe in cartoes:
        partes.append(
            f'<div class="cartao {classe}"><b>{valor}</b><span>{rotulo}</span></div>'
        )
    partes.append("</div>")

    for aviso in resultado.avisos:
        partes.append(f'<div class="aviso">{_html.escape(aviso)}</div>')

    for tabela in tabelas:
        partes.append(
            f'<h2><code>{_html.escape(tabela.nome)}</code> '
            f'<span class="conta">· {tabela.total} linha(s)</span> '
            f"{_etiqueta_origem(tabela.nome)}</h2>"
        )
        partes.append(f'<p class="nota">{_html.escape(tabela.descricao)}</p>')
        if not tabela.linhas:
            partes.append(
                '<div class="rolagem"><div class="vazia">vazia — este documento '
                "não traz este escopo, então o merge não toca nesta tabela</div></div>"
            )
            continue
        partes.append('<div class="rolagem"><table><thead><tr>')
        for coluna in tabela.colunas:
            partes.append(f"<th>{_html.escape(coluna)}</th>")
        partes.append("</tr></thead><tbody>")
        for linha in tabela.linhas:
            partes.append("<tr>")
            for coluna, celula in zip(tabela.colunas, linha):
                classe = ""
                if coluna in ("exemplo", "texto", "texto_origem"):
                    classe = ' class="larga"'
                elif coluna == "chave_natural":
                    classe = ' class="chave"'
                partes.append(f"<td{classe}>{_html.escape(str(celula))}</td>")
            partes.append("</tr>")
        partes.append("</tbody></table></div>")

    gerado = datetime.now().strftime("%d/%m/%Y %H:%M")
    escopos = ", ".join(sorted(str(e) for e in resultado.escopos)) or "nenhum"
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Prévia — {_html.escape(resultado.arquivo)}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="envelope">
  <h1>Prévia de ingestão: <code>{_html.escape(resultado.arquivo)}</code></h1>
  <p class="sub">
    tipo <b>{resultado.tipo}</b> ·
    anos declarados <b>{resultado.anos_declarados or "–"}</b> ·
    e-mail <b>{_html.escape(resultado.identidade.email or "–")}</b><br>
    escopos que este documento atualiza: <code>{_html.escape(escopos)}</code>
  </p>
  {"".join(partes)}
  <footer>
    Nada foi gravado: esta é a prévia do que iria para o banco.
    As chaves naturais e a agregação são as mesmas que a camada de
    persistência usa. Gerado em {gerado}.
  </footer>
</div>
</body>
</html>
"""


# --------------------------------------------------------------------------
# painel de pasta
# --------------------------------------------------------------------------
def painel_html(resultados: list[ResultadoExtracao], pasta: str) -> str:
    """Uma linha por currículo, com os números que iriam para o banco.

    É a visão de conjunto: serve para ver a base inteira de uma vez e para
    achar o documento que saiu estranho.
    """
    total = {
        "skill_sc": 0, "skill_matriz": 0, "skill_comprovada": 0,
        "sem_evidencia": 0, "certificacoes": 0, "experiencias": 0,
        "nao_resolvidas": 0,
    }
    linhas: list[str] = []
    for resultado in sorted(resultados, key=lambda r: -r.resumo()["sem_evidencia"]):
        resumo = resultado.resumo()
        for chave in total:
            total[chave] += resumo[chave]
        # a cor da fila vem do próprio valor; o aviso é coluna separada
        cor_fila = ' style="color:var(--sc);font-weight:600"' if resumo["nao_resolvidas"] else ""
        revisao = '<span class="etiqueta sc">revisar</span>' if resultado.avisos else ""
        linhas.append(
            "<tr>"
            f'<td class="larga" style="white-space:nowrap">{_html.escape(resultado.arquivo)}</td>'
            f"<td>{resultado.tipo}</td>"
            f'<td>{resultado.anos_declarados or "–"}</td>'
            f"<td>{resumo['experiencias']}</td>"
            f"<td>{resumo['certificacoes']}</td>"
            f"<td>{resumo['skill_sc']}</td>"
            f"<td>{resumo['skill_matriz']}</td>"
            f"<td>{resumo['skill_comprovada']}</td>"
            f'<td><b style="color:var(--sc)">{resumo["sem_evidencia"]}</b></td>'
            f"<td{cor_fila}>{resumo['nao_resolvidas']}</td>"
            f"<td>{revisao}</td>"
            "</tr>"
        )

    cartoes = [
        ("currículos", len(resultados), ""),
        ("vínculos", total["experiencias"], ""),
        ("certificações", total["certificacoes"], ""),
        ("skills sem comprovação", total["skill_sc"], "sc"),
        ("skills em tabela", total["skill_matriz"], "mz"),
        ("skills comprovadas", total["skill_comprovada"], "ev"),
        ("afirmadas sem evidência", total["sem_evidencia"], "sc"),
        ("na fila do dicionário", total["nao_resolvidas"], ""),
    ]
    blocos_cartao = "".join(
        f'<div class="cartao {classe}"><b>{valor}</b><span>{rotulo}</span></div>'
        for rotulo, valor, classe in cartoes
    )
    gerado = datetime.now().strftime("%d/%m/%Y %H:%M")
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Painel — {_html.escape(pasta)}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="envelope">
  <h1>Painel de ingestão</h1>
  <p class="sub">{len(resultados)} documento(s) em <code>{_html.escape(pasta)}</code></p>
  <div class="cartoes">{blocos_cartao}</div>
  <h2>Por documento <span class="conta">· ordenado por skills afirmadas sem evidência</span></h2>
  <p class="nota">
    "sem evidência" é a coluna que importa: skill que a pessoa afirma ou lista
    e que nunca aparece dentro de um emprego datado. A última coluna é a fila
    do dicionário — documento com número alto ali tem vocabulário que o
    dicionário ainda não conhece.
  </p>
  <div class="rolagem"><table>
    <thead><tr>
      <th>arquivo</th><th>tipo</th><th>anos</th><th>vínculos</th><th>certs</th>
      <th>skill sc</th><th>matriz</th><th>comprovadas</th>
      <th>sem evidência</th><th>fila</th><th>revisão</th>
    </tr></thead>
    <tbody>{"".join(linhas)}</tbody>
  </table></div>
  <footer>Nada foi gravado: prévia do que iria para o banco. Gerado em {gerado}.</footer>
</div>
</body>
</html>
"""
