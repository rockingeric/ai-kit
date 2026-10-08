"""Claude Code hooks: rebuild after edits in .ai/ or docs/; block commits on the default branch."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from aikit.core import AikitError, current_branch, load_project

GENERATED = {"index.yaml", "manifest.json"}
# `git commit` in command position (start, or after ; && || | ( $( or a newline), with optional
# VAR=x prefixes and git options like -C dir; not `git commit-tree`, not a mention inside text.
_COMMIT_RE = re.compile(
    r"(?:^|[;&|(\n]|\$\()\s*(?:\w+=\S*\s+)*git(?:\s+-[Cc]\s+\S+|\s+--?[\w-]+(?:=\S+)?)*\s+commit(?![\w-])"
)
# Human-only approvals, also when aikit is called by path (`.venv/bin/aikit`).
_HUMAN_ONLY_RE = re.compile(
    r"(?:^|[;&|(\n]|\$\()\s*(?:\w+=\S*\s+)*(?:\S*/)?aikit\s+(adr\s+accept|wish\s+approve)\b"
)


def _payload(stdin: str) -> dict:
    try:
        return json.loads(stdin or "{}")
    except json.JSONDecodeError:
        return {}


def _cwd(payload: dict) -> Path:
    return Path(payload.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())


def watched(project, path: Path) -> bool:
    if path.name in GENERATED and path.parent == project.ai:
        return False
    roots = [project.ai, project.path("docs"), project.path("adr"), project.path("runbooks")]
    return any(path == r or r in path.parents for r in roots)


def post_edit(stdin: str) -> int:
    """Exit 0 = silent; exit 2 = stderr goes back to Claude (PostToolUse cannot block)."""
    from aikit import build

    payload = _payload(stdin)
    file_path = (payload.get("tool_input") or {}).get("file_path")
    if not file_path:
        return 0
    cwd = _cwd(payload)
    try:
        project = load_project(cwd, required=False)
        if not project.config:
            return 0
        path = Path(file_path)
        path = (path if path.is_absolute() else cwd / path).resolve()
        if not watched(project, path):
            return 0
        _, problems = build.run(project)
    except AikitError as exc:
        problems = [str(exc)]
    if problems:
        print("aikit build encontrou problemas:", *problems, sep="\n- ", file=sys.stderr)
        return 2
    return 0


def pre_bash(stdin: str) -> int:
    """Exit 2 blocks the Bash call and shows stderr to Claude."""
    payload = _payload(stdin)
    command = (payload.get("tool_input") or {}).get("command") or ""
    human_only = _HUMAN_ONLY_RE.search(command)
    if human_only:
        action = " ".join(human_only.group(1).split())
        print(
            f"aikit: `aikit {action}` é decisão do humano e não pode ser rodado pelo agente. "
            "Termine pedindo ao humano que rode o comando (no terminal, ou com `!` no Claude Code).",
            file=sys.stderr,
        )
        return 2
    if not _COMMIT_RE.search(command):
        return 0
    try:
        project = load_project(_cwd(payload), required=False)
    except AikitError:
        return 0
    if not project.config or not project.enforce_branches:
        return 0
    branch, default = current_branch(project.root), project.default_branch()
    if branch != default:
        return 0
    print(
        f"aikit: commit na branch padrão ({default}) é bloqueado neste projeto. "
        "Crie a branch do trabalho antes e repita o commit: `git switch -c <tipo>/<slug>` "
        "(wish: `wish/<slug>`, criada pelo `aikit wish approve`). "
        "Desligar: `git: {enforce_branches: false}` em .ai/project.yaml.",
        file=sys.stderr,
    )
    return 2
