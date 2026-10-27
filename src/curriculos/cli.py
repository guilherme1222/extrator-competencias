"""Linha de comando.

    curriculos schema                          aplica/atualiza o schema
    curriculos extrair ARQUIVO                 mostra o que extraiu (sem banco)
    curriculos ingerir ARQUIVO --telefone +55  grava um documento
    curriculos carregar PASTA                  carga inicial de uma pasta
    curriculos revisoes                        fila de revisão humana
    curriculos pendencias                      fila do dicionário
    curriculos pessoa ID                       o que o banco sabe da pessoa

O ponto de entrada do WhatsApp (webhook, download da mídia) não faz parte
deste pacote por decisão de escopo. Quando entrar, ele chama exatamente o
que ``ingerir`` chama: ``ler_arquivo`` -> ``extrair`` -> ``repositorio.ingerir``,
passando o telefone do remetente. Nada aqui precisa mudar.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .dominio import OrigemSkill
from .extracao import extrair
from .leitura import (
    FormatoNaoSuportado,
    SemTextoExtraivel,
    DocumentoInvalido,
    ler_arquivo,
)
from .persistencia import aplicar_schema, conectar, ingerir

EXTENSOES = {".docx", ".pdf"}


def _cmd_schema(args: argparse.Namespace) -> int:
    with conectar(args.dsn) as cx:
        aplicados = aplicar_schema(cx)
    print("schema aplicado:", ", ".join(aplicados))
    return 0


def _cmd_extrair(args: argparse.Namespace) -> int:
    """Dry-run: não toca no banco. Serve para conferir antes de carregar."""
    resultado = extrair(ler_arquivo(args.arquivo))
    print(f"arquivo .......... {resultado.arquivo}")
    print(f"tipo ............. {resultado.tipo.value}")
    print(f"escopos .......... {', '.join(sorted(e.value for e in resultado.escopos)) or '-'}")
    print(f"e-mail ........... {resultado.identidade.email or '-'}")
    print(f"anos declarados .. {resultado.anos_declarados or '-'}")
    for chave, valor in resultado.resumo().items():
        print(f"{chave:.<18} {valor}")

    if resultado.experiencias:
        print("\nEXPERIÊNCIA")
        for exp in resultado.experiencias:
            fim = exp.fim or ("atual" if exp.em_aberto else "?")
            print(
                f"  {exp.inicio or '?'} -> {fim}  "
                f"{(exp.organizacao or '?')[:30]:32s} {(exp.cargo or '')[:34]}"
            )

    if resultado.certificacoes:
        print("\nCERTIFICAÇÃO")
        for cert in resultado.certificacoes:
            print(f"  {cert.sigla:12s} {cert.emissor:16s} {cert.ano or '':4}  {cert.texto_origem[:50]}")

    sem_evidencia = resultado.afirmadas_sem_evidencia()
    if sem_evidencia:
        print(f"\nAFIRMADA SEM EVIDÊNCIA ({len(sem_evidencia)})")
        for fato in sem_evidencia[:20]:
            indice = fato.termo_indice or fato.rotulo_matriz or "-"
            print(f"  {fato.skill:24s} {fato.categoria:12s} via {indice[:24]}")
        if len(sem_evidencia) > 20:
            print(f"  ... e outras {len(sem_evidencia) - 20}")

    for aviso in resultado.avisos:
        print(f"\n[aviso] {aviso}", file=sys.stderr)
    return 0


def _cmd_previa(args: argparse.Namespace) -> int:
    """Prévia do que iria para o banco. Não abre conexão nenhuma."""
    from . import previa as mod_previa

    resultado = extrair(ler_arquivo(args.arquivo))
    tabelas = mod_previa.montar(resultado, telefone=args.telefone)

    print(mod_previa.como_texto(resultado, tabelas, limite=args.limite))

    if args.html:
        destino = Path(args.html)
        destino.write_text(
            mod_previa.como_html(resultado, tabelas), encoding="utf-8"
        )
        print(f"\nHTML escrito em {destino.resolve()}")
    if args.md:
        destino = Path(args.md)
        destino.write_text(
            mod_previa.como_markdown(resultado, tabelas), encoding="utf-8"
        )
        print(f"Markdown escrito em {destino.resolve()}")
    return 0


def _cmd_painel(args: argparse.Namespace) -> int:
    """Painel da pasta inteira. Também não abre conexão."""
    from . import previa as mod_previa

    pasta = Path(args.pasta)
    arquivos = sorted(
        c for c in pasta.iterdir()
        if c.suffix.lower() in EXTENSOES and not c.name.startswith("~$")
    )
    resultados = []
    for caminho in arquivos:
        try:
            resultados.append(extrair(ler_arquivo(caminho)))
        except (SemTextoExtraivel, FormatoNaoSuportado, DocumentoInvalido) as erro:
            print(f"[pulado] {caminho.name}: {erro}", file=sys.stderr)
    if not resultados:
        print(f"nenhum documento legível em {pasta}", file=sys.stderr)
        return 1

    destino = Path(args.html)
    destino.write_text(
        mod_previa.painel_html(resultados, str(pasta)), encoding="utf-8"
    )
    print(f"{len(resultados)} documento(s) · painel em {destino.resolve()}")
    return 0


def _ingerir_um(cx, caminho: Path, telefone, cpf, nome, chave_externa) -> str:
    try:
        arquivo = ler_arquivo(caminho)
    except SemTextoExtraivel as erro:
        return f"REVISAO  {caminho.name}: {erro}"
    except (FormatoNaoSuportado, DocumentoInvalido) as erro:
        return f"ERRO     {caminho.name}: {erro}"

    resultado = extrair(arquivo)
    ingestao = ingerir(
        cx,
        resultado,
        formato=arquivo.formato,
        telefone=telefone,
        cpf=cpf,
        nome=nome,
        chave_externa=chave_externa,
    )
    return f"{ingestao.status:9s} {caminho.name}: {ingestao}"


def _cmd_ingerir(args: argparse.Namespace) -> int:
    caminho = Path(args.arquivo)
    with conectar(args.dsn) as cx:
        print(
            _ingerir_um(
                cx,
                caminho,
                telefone=args.telefone,
                cpf=args.cpf,
                nome=args.nome,
                chave_externa=None if args.telefone or args.cpf else f"arquivo:{caminho.name}",
            )
        )
    return 0


def _cmd_carregar(args: argparse.Namespace) -> int:
    """Carga inicial de uma pasta.

    Documento de pasta não tem telefone, então a identidade é
    ``arquivo:<nome>`` na coluna ``chave_externa``. Quando a pessoa mandar
    algo pelo WhatsApp depois, basta preencher ``telefone_e164`` na linha
    que já existe.
    """
    pasta = Path(args.pasta)
    arquivos = sorted(
        c
        for c in pasta.iterdir()
        if c.suffix.lower() in EXTENSOES and not c.name.startswith("~$")
    )
    if not arquivos:
        print(f"nenhum .docx/.pdf em {pasta}", file=sys.stderr)
        return 1

    contagem = {"PROCESSADO": 0, "REVISAO": 0, "ERRO": 0, "JA": 0}
    with conectar(args.dsn) as cx:
        for caminho in arquivos:
            linha = _ingerir_um(
                cx,
                caminho,
                telefone=None,
                cpf=None,
                nome=None,
                chave_externa=f"arquivo:{caminho.name}",
            )
            if args.verboso:
                print(linha)
            if "já processado" in linha:
                contagem["JA"] += 1
            else:
                contagem[linha.split()[0]] = contagem.get(linha.split()[0], 0) + 1

    print(
        f"{len(arquivos)} arquivo(s): "
        + ", ".join(f"{k.lower()}={v}" for k, v in contagem.items() if v)
    )
    return 0


def _cmd_revisoes(args: argparse.Namespace) -> int:
    with conectar(args.dsn) as cx:
        linhas = cx.execute(
            """
            select r.id_revisao, r.motivo, d.nome_arquivo, r.detalhe
              from revisao r
              left join documento d on d.id_documento = r.id_documento
             where r.resolvido_em is null
             order by r.criado_em
             limit %s
            """,
            (args.limite,),
        ).fetchall()
    if not linhas:
        print("nenhuma revisão aberta")
        return 0
    for id_revisao, motivo, arquivo, detalhe in linhas:
        print(f"#{id_revisao} {motivo:22s} {(arquivo or '-')[:34]:36s} {(detalhe or '')[:70]}")
    return 0


def _cmd_pendencias(args: argparse.Namespace) -> int:
    """Linhas que viraram afirmação mas não renderam skill.

    É a fila para ampliar o dicionário: o termo que mais repete aqui é o
    próximo a ser cadastrado.
    """
    with conectar(args.dsn) as cx:
        linhas = cx.execute(
            """
            select count(*) as vezes, termo_indice, min(texto) as exemplo
              from linha_nao_resolvida
             where resolvida_em is null
             group by termo_indice
             order by vezes desc
             limit %s
            """,
            (args.limite,),
        ).fetchall()
    if not linhas:
        print("nenhuma pendência")
        return 0
    for vezes, termo, exemplo in linhas:
        print(f"{vezes:4d}x via {(termo or '-'):18s} | {exemplo[:80]}")
    return 0


def _cmd_pessoa(args: argparse.Namespace) -> int:
    with conectar(args.dsn) as cx:
        cabecalho = cx.execute(
            """
            select nome, telefone_e164, cpf, email, chave_externa
              from pessoa where id_pessoa = %s
            """,
            (args.id_pessoa,),
        ).fetchone()
        if not cabecalho:
            print(f"pessoa {args.id_pessoa} não existe", file=sys.stderr)
            return 1
        nome, telefone, cpf, email, chave = cabecalho
        print(f"pessoa {args.id_pessoa}: {nome or '?'}")
        print(f"  telefone={telefone or '-'} cpf={cpf or '-'} email={email or '-'} chave={chave or '-'}")

        for titulo, sql in (
            (
                "EXPERIÊNCIA",
                """select inicio, fim, em_aberto, organizacao, cargo
                     from experiencia where id_pessoa = %s and removido_em is null
                    order by inicio desc nulls last""",
            ),
            (
                "CERTIFICAÇÃO",
                """select sigla, emissor, ano from certificacao
                    where id_pessoa = %s and removido_em is null order by sigla""",
            ),
        ):
            linhas = cx.execute(sql, (args.id_pessoa,)).fetchall()
            if linhas:
                print(f"\n{titulo}")
                for linha in linhas:
                    print("  " + "  ".join(str(c) for c in linha if c is not None))

        sem = cx.execute(
            """
            select categoria, count(*), string_agg(skill, ', ' order by mencoes desc)
              from vw_skill_sem_evidencia where id_pessoa = %s
             group by categoria order by 2 desc
            """,
            (args.id_pessoa,),
        ).fetchall()
        if sem:
            print("\nAFIRMADA SEM EVIDÊNCIA")
            for categoria, quantas, skills in sem:
                print(f"  {categoria:12s} ({quantas:2d}) {skills[:90]}")

        comp = cx.execute(
            """
            select count(*) from vw_skill_comprovada where id_pessoa = %s
            """,
            (args.id_pessoa,),
        ).fetchone()[0]
        print(f"\ncomprovadas (dentro de vínculo datado): {comp}")
    return 0


def main(argv: list[str] | None = None) -> int:
    pai = argparse.ArgumentParser(
        prog="curriculos",
        description="Extrai competências de currículos e certificados e grava no banco",
    )
    pai.add_argument(
        "--dsn",
        default=None,
        help="DSN do PostgreSQL (padrão: $DATABASE_URL)",
    )
    sub = pai.add_subparsers(dest="comando", required=True)

    s = sub.add_parser("schema", help="aplica o schema")
    s.set_defaults(func=_cmd_schema)

    s = sub.add_parser("extrair", help="mostra o que extraiu, sem gravar")
    s.add_argument("arquivo")
    s.set_defaults(func=_cmd_extrair)

    s = sub.add_parser(
        "previa",
        help="mostra as linhas que iriam para o banco (sem banco, sem gravar)",
    )
    s.add_argument("arquivo")
    s.add_argument("--html", metavar="SAIDA.html", help="também escreve uma página HTML")
    s.add_argument("--md", metavar="SAIDA.md", help="também escreve markdown (Ctrl+Shift+V no VS Code)")
    s.add_argument("--telefone", help="simula a chegada pelo WhatsApp com este número")
    s.add_argument("--limite", type=int, default=12, help="linhas por tabela no terminal")
    s.set_defaults(func=_cmd_previa)

    s = sub.add_parser("ingerir", help="grava um documento")
    s.add_argument("arquivo")
    s.add_argument("--telefone", help="número de quem enviou, em E.164")
    s.add_argument("--cpf")
    s.add_argument("--nome")
    s.set_defaults(func=_cmd_ingerir)

    s = sub.add_parser("carregar", help="carga inicial de uma pasta")
    s.add_argument("pasta")
    s.add_argument("-v", "--verboso", action="store_true")
    s.set_defaults(func=_cmd_carregar)

    s = sub.add_parser(
        "painel",
        help="HTML com uma linha por documento da pasta (sem banco)",
    )
    s.add_argument("pasta")
    s.add_argument("--html", default="painel.html", metavar="SAIDA.html")
    s.set_defaults(func=_cmd_painel)

    s = sub.add_parser("revisoes", help="fila de revisão humana")
    s.add_argument("--limite", type=int, default=40)
    s.set_defaults(func=_cmd_revisoes)

    s = sub.add_parser("pendencias", help="fila do dicionário")
    s.add_argument("--limite", type=int, default=30)
    s.set_defaults(func=_cmd_pendencias)

    s = sub.add_parser("pessoa", help="o que o banco sabe de uma pessoa")
    s.add_argument("id_pessoa", type=int)
    s.set_defaults(func=_cmd_pessoa)

    args = pai.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
