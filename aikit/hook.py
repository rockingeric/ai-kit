"""Claude Code hooks: rebuild after edits in .ai/ or docs/; block commits on the default branch."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from aikit.core import AikitError, current_branch, git, load_project

GENERATED = {"index.yaml", "manifest.json"}
# `git commit` in command position (start, or after ; && || | ( $( or a newline), with optional
# VAR=x prefixes and git options like -C dir; not `git commit-tree`, not a mention inside text.
_COMMIT_RE = re.compile(
    r"(?:^|[;&|(\n]|\$\()\s*(?:\w+=\S*\s+)*git((?:\s+-[Cc]\s+\S+|\s+--?[\w-]+(?:=\S+)?)*)\s+commit(?![\w-])"
)
# `cd dir` in command position; the commit runs where the last cd before it left the shell.
_CD_RE = re.compile(r"(?:^|[;&|(\n])\s*cd\s+(\S+)")
_GIT_C_RE = re.compile(r"-C\s+(\S+)")
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
    """`path` absolute but unresolved: a linked folder (e.g. shared wishes) counts by where it is linked."""
    roots = [project.ai, project.path("docs"), project.path("adr"), project.path("runbooks")]
    for candidate in {Path(os.path.normpath(path)), path.resolve()}:
        if candidate.name in GENERATED and candidate.parent in (project.ai, project.ai.resolve()):
            return False
        for root in roots:
            for r in {root, root.resolve()}:
                if candidate == r or r in candidate.parents:
                    return True
    return False


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
        path = path if path.is_absolute() else cwd / path
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
    cwd = _cwd(payload)
    default = next(filter(None, (_blocked(cwd, command, m) for m in _COMMIT_RE.finditer(command))), None)
    if default is None:
        return 0
    print(
        f"aikit: commit na branch padrão ({default}) é bloqueado neste projeto. "
        "Crie a branch do trabalho antes e repita o commit: `git switch -c <tipo>/<slug>` "
        "(wish: `wish/<slug>`, criada pelo `aikit wish approve`). "
        "Desligar: `git: {enforce_branches: false}` em .ai/project.yaml.",
        file=sys.stderr,
    )
    return 2


def _dir(base: Path, arg: str) -> Path:
    path = Path(os.path.expandvars(os.path.expanduser(arg.strip("'\""))))
    return path if path.is_absolute() else base / path


def _commit_dir(cwd: Path, command: str, match: re.Match) -> Path:
    """Where a commit runs: session cwd, then each `cd` before it, then its `git -C`."""
    where = cwd
    for cd in _CD_RE.finditer(command, 0, match.start() + 1):
        where = _dir(where, cd.group(1))
    for c in _GIT_C_RE.finditer(match.group(1)):
        where = _dir(where, c.group(1))
    # A dir that does not exist yet (or a typo) is judged by its nearest existing parent.
    while not where.is_dir() and where != where.parent:
        where = where.parent
    return where


def _blocked(cwd: Path, command: str, match: re.Match) -> str | None:
    """The default branch when this commit would land on it; None otherwise."""
    where = _commit_dir(cwd, command, match)
    try:
        project = load_project(where, required=False)
        if not project.config:
            # A worktree without .ai/ (it is excluded, not tracked) follows the session's project.
            session = load_project(cwd, required=False)
            shared = _common_dir(where)
            if not session.config or shared is None or shared != _common_dir(session.root):
                return None
            project = session
    except AikitError:
        return None
    if not project.enforce_branches:
        return None
    default = project.default_branch()
    return default if current_branch(where) == default else None


def _common_dir(path: Path) -> Path | None:
    out = git(path, "rev-parse", "--path-format=absolute", "--git-common-dir")
    return Path(out).resolve() if out else None
