"""`aikit init` / `aikit uninstall`: everything kit-owned is tracked in .ai/manifest.json."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from aikit import __version__, build, exclude
from aikit.core import (
    AI_DIR,
    AikitError,
    Project,
    git_toplevel,
    is_tracked,
    kit_root,
    load_project,
    load_yaml,
    scalar,
    today,
    write_if_changed,
)

IMPORT_LINE = "@.ai/AGENTS.md"
HOOK_MARK = "aikit hook "
BASE_EXCLUDES = ["/.ai/", "/.claude/agents/aikit-*", "/.claude/skills/aikit-*", "/.claude/settings.local.json"]


def _template(filename: str, **values: str) -> str:
    text = (kit_root() / "templates" / filename).read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def hook_entries() -> dict[str, dict]:
    """Event name -> our settings entry, from hooks/hooks.json."""
    entries = json.loads((kit_root() / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    exe = shutil.which("aikit")
    if not exe and Path(sys.argv[0]).name == "aikit":  # running from a hook whose shell lacks PATH
        exe = str(Path(sys.argv[0]).absolute())  # not resolve(): keep the same symlink path `which` gives
    if exe:  # absolute path: the hook shell may not share the user's PATH
        for entry in entries.values():
            for hook in entry["hooks"]:
                hook["command"] = hook["command"].replace("aikit ", f"{exe} ", 1)
    return entries


def _is_ours(entry: dict) -> bool:
    return any(HOOK_MARK in h.get("command", "") for h in entry.get("hooks", []))


def merged_settings(path: Path) -> str:
    """settings.local.json content with our hook entries added, everything else kept."""
    settings = json.loads(path.read_text(encoding="utf-8") or "{}") if path.is_file() else {}
    hooks = settings.setdefault("hooks", {})
    for event, entry in hook_entries().items():
        current = hooks.setdefault(event, [])
        current[:] = [e for e in current if not _is_ours(e)] + [entry]
    return json.dumps(settings, indent=2, ensure_ascii=False) + "\n"


def merge_settings(path: Path) -> bool:
    """Returns True if the file was created."""
    created = not path.exists()
    write_if_changed(path, merged_settings(path))
    return created


def unmerge_settings(path: Path, created: bool) -> None:
    if not path.is_file():
        return
    settings = json.loads(path.read_text(encoding="utf-8") or "{}")
    hooks = settings.get("hooks", {})
    for event in list(hooks):
        kept = [e for e in hooks[event] if not _is_ours(e)]
        if kept:
            hooks[event] = kept
        else:
            hooks.pop(event)
    if not hooks:
        settings.pop("hooks", None)
    if created and not settings:
        path.unlink()
    else:
        path.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _append_import(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if IMPORT_LINE in text.split():
        return False
    path.write_text(text.rstrip("\n") + ("\n\n" if text.strip() else "") + IMPORT_LINE + "\n", encoding="utf-8")
    return True


def init(start: Path, overlays: list[str]) -> list[str]:
    root = git_toplevel(start) or start.resolve()
    project = Project(root)
    previous = project.manifest() if (project.ai / "manifest.json").is_file() else {}
    files: set[str] = set(previous.get("files", []))
    edits: list[dict] = list(previous.get("edits", []))
    kept = [e for e in previous.get("exclude", []) if e not in BASE_EXCLUDES and e != "/.genie/"]
    excludes = BASE_EXCLUDES + kept
    notes: list[str] = []

    kit = kit_root()
    for overlay in overlays:
        if not (kit / "overlays" / overlay).is_dir():
            raise AikitError(f"overlay '{overlay}' não existe em {kit / 'overlays'}")

    (project.ai / "personas").mkdir(parents=True, exist_ok=True)
    cfg = project.ai / "project.yaml"
    if not cfg.exists():
        cfg.write_text(_template("project.yaml", name=scalar(root.name)), encoding="utf-8")
    project = Project(root, load_yaml(cfg) or {})
    agents_md = project.ai / "AGENTS.md"
    if not agents_md.exists():
        agents_md.write_text(_template("AGENTS.md", name=project.name), encoding="utf-8")
    if overlays:
        path = project.ai / "overlays.yaml"
        current = (load_yaml(path) or []) if path.is_file() else []
        merged = current + [o for o in overlays if o not in current]
        path.write_text("".join(f"- {o}\n" for o in merged), encoding="utf-8")

    for key in ("adr", "runbooks"):
        project.path(key).mkdir(parents=True, exist_ok=True)

    claude_md = root / "CLAUDE.md"
    if not claude_md.exists():
        claude_md.write_text(_template("CLAUDE.md"), encoding="utf-8")
        files.add("CLAUDE.md")
        excludes.append("/CLAUDE.md")
    elif is_tracked(root, "CLAUDE.md"):
        local = root / "CLAUDE.local.md"
        if not local.exists():
            local.write_text(_template("CLAUDE.md"), encoding="utf-8")
            files.add("CLAUDE.local.md")
            excludes.append("/CLAUDE.local.md")
        elif _append_import(local):
            edits.append({"file": "CLAUDE.local.md", "line": IMPORT_LINE})
        notes.append("CLAUDE.md é do time (versionado): não mexi nele; o import foi para CLAUDE.local.md")
    elif _append_import(claude_md):
        edits.append({"file": "CLAUDE.md", "line": IMPORT_LINE})

    agents_link = root / "AGENTS.md"
    if not agents_link.exists() and not agents_link.is_symlink():
        agents_link.symlink_to(Path(AI_DIR) / "AGENTS.md")
        files.add("AGENTS.md")
        excludes.append("/AGENTS.md")
    elif not agents_link.is_symlink():
        notes.append("AGENTS.md já existe: não mexi nele (Codex e Cursor continuam lendo o do time)")

    settings_path = root / ".claude" / "settings.local.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    created = merge_settings(settings_path)
    settings_created = previous.get("settings_created", created)

    manifest = {
        "kit_version": __version__,
        "installed": previous.get("installed", today().isoformat()),
        "files": sorted(files),
        "edits": edits,
        "settings_created": settings_created,
        "exclude": list(dict.fromkeys(excludes)),
        "last_backup": previous.get("last_backup"),
    }
    project.save_manifest(manifest)
    if not exclude.write_block(root, manifest["exclude"]):
        notes.append("sem repositório git: nada foi adicionado a .git/info/exclude")

    changed, problems = build.run(project)
    notes += [f"build: {p}" for p in problems]
    return notes


def uninstall(start: Path, assume_yes: bool) -> list[str]:
    from aikit import backup

    project = load_project(start)
    root = project.root
    manifest = project.manifest()
    notes: list[str] = []

    user_content = [p for p in project.ai.rglob("*") if p.is_file() and p.name not in ("index.yaml", "manifest.json")]
    if user_content:
        if backup.configured_dir():
            notes.append(f"backup de .ai/ em {backup.run(project)}")
        elif not assume_yes:
            raise AikitError(
                ".ai/ tem conteúdo seu (project.yaml, AGENTS.md, overrides, notas) e não há backup "
                "configurado. Rode `aikit backup --to <dir>` antes, ou repita com --yes para apagar."
            )

    for rel in manifest.get("files", []):
        path = root / rel
        if path.is_symlink() or path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
        parent = path.parent
        while parent != root and parent.is_dir() and not any(parent.iterdir()):
            parent.rmdir()
            parent = parent.parent
    for edit in manifest.get("edits", []):
        path = root / edit["file"]
        if path.is_file():
            lines = path.read_text(encoding="utf-8").split("\n")
            kept = [line for line in lines if line.strip() != edit["line"]]
            path.write_text("\n".join(kept).rstrip("\n") + "\n", encoding="utf-8")

    unmerge_settings(root / ".claude" / "settings.local.json", manifest.get("settings_created", False))
    exclude.remove_block(root)
    shutil.rmtree(project.ai)
    claude_dir = root / ".claude"
    if claude_dir.is_dir() and not any(claude_dir.iterdir()):
        claude_dir.rmdir()
    notes.append("docs/ ficou intacto: é do time")
    return notes
