"""Claude Code hooks: rebuild after edits in .ai/ or docs/; block commits on the default branch."""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path

from aikit.core import AI_DIR, AikitError, current_branch, git, git_toplevel, load_project

GENERATED = {"index.yaml", "manifest.json"}
# `git commit` in command position (start, or after ; && || | ( $( or a newline), with optional
# VAR=x prefixes and git options like -C dir; not `git commit-tree`, not a mention inside text.
_COMMIT_RE = re.compile(
    r"(?:^|[;&|(\n]|\$\()\s*(?:\w+=\S*\s+)*git((?:\s+-[Cc]\s+\S+|\s+--?[\w-]+(?:=\S+)?)*)\s+commit(?![\w-])"
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


def _commit_dir(cwd: Path, command: str, match: re.Match) -> Path | None:
    """Where a commit runs, read only from the form `cd a && git add . && git -C b commit`.

    An allowlist: before the commit only `cd <literal dir>` and plain `git ...` segments, joined by
    `&&`. Anything the shell could read differently from shlex (other commands, ; | ( ` newline,
    # $ ~, GIT_* vars, CDPATH, a dir that does not exist) gives None: the caller then judges by
    the session cwd, as before.
    """
    text = command[: match.end()]
    if any(c in text for c in "\n`#$"):
        return None
    try:
        lexer = shlex.shlex(text, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        return None
    if any(t.startswith("~") for t in tokens):
        return None
    segments: list[list[str]] = [[]]
    for token in tokens:
        if token == "&&":
            segments.append([])
        elif set(token) <= set(";&|()<>{}!"):
            return None
        else:
            segments[-1].append(token)
    where = cwd
    for words in segments[:-1]:
        if words[:1] == ["git"]:
            continue
        if len(words) != 2 or words[0] != "cd" or words[1].startswith("-"):
            return None
        if os.environ.get("CDPATH") and not words[1].startswith(("/", ".")):
            return None
        where = Path(os.path.normpath(where / words[1]))  # logical, like the shell's cd
        if not where.is_dir():
            return None
    words = segments[-1]
    while words and "=" in words[0]:
        if words[0].startswith("GIT_"):
            return None
        words = words[1:]
    args = iter(words[1:])  # after `git`
    for word in args:
        if word == "commit":
            break
        if word == "-C":
            where = where / next(args, "")  # physical, like git's chdir
        elif word == "-c":
            next(args, None)
        elif word.startswith(("--git-dir", "--work-tree")):
            return None
    return where if where.is_dir() else None


def _blocked(cwd: Path, command: str, match: re.Match) -> str | None:
    """The default branch when this commit would land on it; None otherwise.

    The policy is the session project's for any checkout of the same repo (a worktree has no .ai/:
    it is excluded, not tracked); another repo is judged only by .ai/ at its own top level.
    """
    where = _commit_dir(cwd, command, match) or cwd
    try:
        session = load_project(cwd, required=False)
        if where == cwd or _common_dir(where) == _common_dir(session.root):
            project = session
        else:
            top = git_toplevel(where)
            if top is None or not (top / AI_DIR / "project.yaml").is_file():
                return None
            project = load_project(top)
    except AikitError:
        return None
    if not project.config or not project.enforce_branches:
        return None
    default = project.default_branch()
    return default if current_branch(where) == default else None


def _common_dir(path: Path) -> Path | None:
    out = git(path, "rev-parse", "--path-format=absolute", "--git-common-dir")
    return Path(out).resolve() if out else None
