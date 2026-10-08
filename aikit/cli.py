"""`aikit` command line."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from aikit import __version__
from aikit.core import AikitError, load_project


def _tags(value: str | None) -> list[str]:
    return [t.strip() for t in value.split(",") if t.strip()] if value else []


def _rebuild(project) -> int:
    """Mutating commands rebuild implicitly, so the index never lags behind the files."""
    from aikit import build

    _, problems = build.run(project)
    for problem in problems:
        print(f"aviso (build): {problem}", file=sys.stderr)
    return 0


def cmd_init(args) -> int:
    from aikit import install

    for note in install.init(Path.cwd(), args.overlay or []):
        print(f"- {note}")
    print("ai-kit instalado. Próximo passo: abra o Claude Code neste projeto e rode /aikit-onboard")
    return 0


def cmd_build(args) -> int:
    from aikit import build

    project = load_project()
    changed, problems = build.run(project)
    if not args.quiet:
        print("\n".join(f"atualizado: {c}" for c in changed) or "build em dia")
    for problem in problems:
        print(f"erro: {problem}", file=sys.stderr)
    return 1 if problems else 0


def cmd_lint(args) -> int:
    from aikit import lint

    report = lint.run(load_project(), refs=args.refs)
    for err in report.errors:
        print(f"ERRO  {err}")
    for warn in report.warnings:
        print(f"AVISO {warn}")
    if not report.errors and not report.warnings:
        print("lint ok")
    return 1 if report.errors else 0


def cmd_adr(args) -> int:
    from aikit import records

    project = load_project()
    if args.action == "new":
        path = records.new_adr(project, args.title, _tags(args.tags), args.summary, args.supersedes)
        n = path.name[4:8]
        print(project.rel(path))
        print(f"Preencha Contexto, Opções, Decisão e Consequências. Para aceitar: aikit adr accept {n}")
    elif args.action == "supersede":
        old, new = records.supersede(project, args.old, args.new)
        print(f"{old.name[:8]} superseded por {new.name[:8]}")
    elif args.action == "accept":
        path, changed = records.accept(project, args.ref)
        print(f"{path.name[:8]} accepted (body_sha gravado)" if changed else f"{path.name[:8]} já estava accepted")
    elif args.action == "reject":
        path = records.reject(project, args.ref)
        print(f"{path.name[:8]} rejected")
    return _rebuild(project)


def cmd_runbook(args) -> int:
    from aikit import records

    project = load_project()
    if args.action == "new":
        path = records.new_runbook(project, args.title, args.trigger, _tags(args.tags), args.summary)
        print(project.rel(path))
    else:
        path = records.verify_runbook(project, args.ref)
        print(f"{project.rel(path)}: last_verified atualizado")
    return _rebuild(project)


def cmd_plan(args) -> int:
    from aikit import records

    project = load_project()
    if args.action == "new":
        path, branch_note = records.new_plan(project, args.title, args.summary)
        print(project.rel(path))
        if branch_note:
            print(branch_note)
        print("Preencha Objetivo, Escopo, Critérios de aceite e Passos.")
    else:
        path, open_items = records.finish_plan(project, args.ref)
        print(f"{project.rel(path)}: done (saiu do índice)")
        for item in open_items:
            print(f"aviso: critério não marcado: {item}", file=sys.stderr)
    return _rebuild(project)


def cmd_backup(args) -> int:
    from aikit import backup

    target = backup.run(load_project(), Path(args.to) if args.to else None)
    print(f"backup em {target}")
    return 0


def cmd_doctor(args) -> int:
    from aikit import doctor

    problems, warnings = doctor.run(load_project())
    for p in problems:
        print(f"ERRO  {p}")
    for w in warnings:
        print(f"AVISO {w}")
    if not problems and not warnings:
        print("tudo certo")
    return 1 if problems else 0


def cmd_uninstall(args) -> int:
    from aikit import install

    for note in install.uninstall(Path.cwd(), args.yes):
        print(f"- {note}")
    print("ai-kit removido")
    return 0


def cmd_hook(args) -> int:
    from aikit import hook

    handler = hook.pre_bash if args.event == "pre-bash" else hook.post_edit
    return handler(sys.stdin.read())


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="aikit", description="Personas, ADRs e contexto enxuto para coding agents.")
    p.add_argument("--version", action="version", version=f"aikit {__version__}")
    sub = p.add_subparsers(dest="command", required=True, metavar="<comando>")

    s = sub.add_parser("init", help="instala o kit no projeto atual")
    s.add_argument("--overlay", action="append", help="overlay de domínio (repetível)")
    s.set_defaults(func=cmd_init)

    s = sub.add_parser("build", help="compila personas e regenera o índice")
    s.add_argument("-q", "--quiet", action="store_true")
    s.set_defaults(func=cmd_build)

    s = sub.add_parser("lint", help="valida schemas, ADRs, tipos Diátaxis e orçamentos")
    s.add_argument("--refs", action="store_true", help="também acusa paths citados em docs que não existem")
    s.set_defaults(func=cmd_lint)

    adr = sub.add_parser("adr", help="ciclo de vida dos ADRs").add_subparsers(dest="action", required=True)
    s = adr.add_parser("new", help="novo ADR (proposed)")
    s.add_argument("title")
    s.add_argument("--tags", help="separadas por vírgula")
    s.add_argument("--summary", help="até 80 caracteres")
    s.add_argument("--supersedes", help="ADR que este substitui")
    s = adr.add_parser("supersede", help="marca OLD como substituído por NEW")
    s.add_argument("old")
    s.add_argument("new")
    s = adr.add_parser("accept", help="aceita e congela o corpo (só humano)")
    s.add_argument("ref")
    s = adr.add_parser("reject", help="rejeita um ADR proposed")
    s.add_argument("ref")
    for name in ("new", "supersede", "accept", "reject"):
        adr.choices[name].set_defaults(func=cmd_adr)

    rb = sub.add_parser("runbook", help="runbooks operacionais").add_subparsers(dest="action", required=True)
    s = rb.add_parser("new", help="novo runbook")
    s.add_argument("title")
    s.add_argument("--trigger", help="sintoma que dispara o runbook")
    s.add_argument("--tags", help="separadas por vírgula")
    s.add_argument("--summary", help="até 80 caracteres")
    s = rb.add_parser("verify", help="marca o runbook como verificado hoje")
    s.add_argument("ref")
    for name in ("new", "verify"):
        rb.choices[name].set_defaults(func=cmd_runbook)

    pl = sub.add_parser("plan", help="planos de trabalho que atravessam sessões").add_subparsers(
        dest="action", required=True
    )
    s = pl.add_parser("new", help="novo plano (active) em .ai/plans")
    s.add_argument("title")
    s.add_argument("--summary", help="até 80 caracteres")
    s = pl.add_parser("done", help="conclui o plano e o tira do índice")
    s.add_argument("ref")
    for name in ("new", "done"):
        pl.choices[name].set_defaults(func=cmd_plan)

    s = sub.add_parser("backup", help="copia .ai/ para seu repo privado de backup")
    s.add_argument("--to", help="diretório de backup (fica salvo para as próximas vezes)")
    s.set_defaults(func=cmd_backup)

    s = sub.add_parser("doctor", help="checa a saúde da instalação")
    s.set_defaults(func=cmd_doctor)

    s = sub.add_parser("uninstall", help="remove o kit; docs/ fica")
    s.add_argument("--yes", action="store_true", help="apaga .ai/ mesmo sem backup configurado")
    s.set_defaults(func=cmd_uninstall)

    s = sub.add_parser("hook", help="entrada dos hooks do Claude Code")
    s.add_argument("event", choices=["post-edit", "pre-bash"])
    s.set_defaults(func=cmd_hook)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        return args.func(args)
    except AikitError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 1
