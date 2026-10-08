"""`aikit doctor`: is this project's install healthy and current?"""

from __future__ import annotations

import datetime as dt
import json
import shutil

from aikit import __version__, build, exclude
from aikit.core import Project, today
from aikit.install import HOOK_MARK, IMPORT_LINE

BACKUP_MAX_AGE_DAYS = 7


def run(project: Project) -> tuple[list[str], list[str]]:
    """Return (problems, warnings); empty lists mean healthy."""
    root = project.root
    problems: list[str] = []
    warnings: list[str] = []
    manifest = project.manifest()

    if not (project.ai / "manifest.json").is_file():
        problems.append("sem .ai/manifest.json: rode `aikit init`")

    block = exclude.read_block(root)
    if block is None:
        problems.append("bloco ai-kit ausente em .git/info/exclude: rode `aikit init`")
    elif "/.ai/" not in block:
        problems.append(".ai/ não está no exclude: rode `aikit init`")

    agents_md = project.ai / "AGENTS.md"
    if agents_md.is_file() and "TODO" in agents_md.read_text(encoding="utf-8"):
        warnings.append(".ai/AGENTS.md ainda tem TODO: rode /aikit-onboard no Claude Code")

    imports = [p for p in ("CLAUDE.md", "CLAUDE.local.md") if (root / p).is_file()
               and IMPORT_LINE in (root / p).read_text(encoding="utf-8").split()]
    if not imports:
        problems.append(f"nem CLAUDE.md nem CLAUDE.local.md importam {IMPORT_LINE}")
    link = root / "AGENTS.md"
    if "AGENTS.md" in manifest.get("files", []) and not (link.is_symlink() and link.exists()):
        problems.append("AGENTS.md devia ser symlink para .ai/AGENTS.md: rode `aikit init`")

    settings = root / ".claude" / "settings.local.json"
    hooks = json.loads(settings.read_text(encoding="utf-8")).get("hooks", {}) if settings.is_file() else {}
    for event in ("PostToolUse", "PreToolUse"):
        if not any(HOOK_MARK in h.get("command", "") for e in hooks.get(event, []) for h in e.get("hooks", [])):
            problems.append(f"hook {event} do kit ausente em .claude/settings.local.json: rode `aikit build`")
    if not shutil.which("aikit"):
        warnings.append("`aikit` fora do PATH: o hook pode não rodar (uv tool install -e ~/ai-kit)")

    build_plan = build.plan(project)
    pending = build_plan.pending()
    if pending:
        names = ", ".join(project.rel(p) for p in pending[:3]) + ("…" if len(pending) > 3 else "")
        problems.append(f"build desatualizado ({names}): rode `aikit build`")
    if build_plan.problems:
        problems.append(f"{len(build_plan.problems)} problema(s) no build: rode `aikit lint`")

    installed = manifest.get("kit_version")
    if installed and installed != __version__:
        warnings.append(f"projeto construído com o kit {installed}; kit atual é {__version__}: rode `aikit build`")

    last = manifest.get("last_backup")
    if not last:
        warnings.append("nunca teve backup do .ai/: rode `aikit backup`")
    else:
        age = (today() - dt.date.fromisoformat(last)).days
        if age > BACKUP_MAX_AGE_DAYS:
            warnings.append(f"último backup há {age} dias: rode `aikit backup`")
    return problems, warnings
