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
# Above this the regexes could take seconds (VAR=x prefixes backtrack); a timed-out hook does not block.
MAX_COMMAND = 8192
# rtk's Claude Code hook rewrites `git commit` to `rtk git commit`: `[path/]rtk [-opts] [proxy [-opts]]`
# runs what follows. Options may carry `=value`. No operator in the path: linear on long runs of `;`.
_RTK_OPTS_RE = r"(?:\s+-[\w-]+(?:=[^\s;&|()]*)?)*"
_WRAPPER_RE = r"(?:(?:[^\s;&|()]*/)?rtk" + _RTK_OPTS_RE + r"\s+(?:proxy" + _RTK_OPTS_RE + r"\s+)?)?"
# A command in command position (start, or after ; && || | ( $( or a newline, with optional VAR=x
# prefixes and an rtk wrapper), or called by any path: `/git`, `.venv/bin/aikit`, `$(cd .. && pwd)/git`.
# The path itself is not parsed, so a `$(...)` with spaces or nesting cannot hide it.
# VAR=x values: no operator inside except a whole `$(...)`, so prefixes do not backtrack.
_ASSIGN_RE = r"(?:\w+=(?:\$\([^()\s]*\)|[^\s;&|()])*\s+)*"
_COMMAND_RE = r"(?:(?:^|[;&|(\n]|\$\()\s*" + _ASSIGN_RE + _WRAPPER_RE + r"|/)"
# `git commit` with git options like -C dir; not `git commit-tree`, not a mention inside text.
_COMMIT_RE = re.compile(
    _COMMAND_RE + r"git((?:\s+-[Cc]\s+\S+|\s+--?[\w-]+(?:=\S+)?)*)\s+commit(?![\w-])"
)
# Before a commit, only these leave HEAD, the branch and the git dir where the hook saw them.
_SAFE_GIT = {"add", "rm", "mv", "status", "diff", "log", "show", "commit"}
_OPERATORS = set(";&|()<>{}!")
# Human-only approvals, also when aikit is called by path (`.venv/bin/aikit`).
_HUMAN_ONLY_RE = re.compile(_COMMAND_RE + r"aikit\s+(adr\s+accept|wish\s+approve)\b")


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
    if len(command) > MAX_COMMAND and ("commit" in command or "aikit" in command):
        print(
            f"aikit: comando com mais de {MAX_COMMAND} caracteres que menciona commit ou aikit; "
            "o hook não o confere. Divida o comando, ou escreva o conteúdo longo em arquivo "
            "(Write) e passe o arquivo (ex.: `git commit -F arquivo`).",
            file=sys.stderr,
        )
        return 2
    if len(command) > MAX_COMMAND:
        return 0
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

    An allowlist: before the commit only `cd <literal dir>` and `git <subcommand>` for subcommands
    that cannot move HEAD, the branch or the git dir (`worktree add`, `switch`, `init
    --separate-git-dir` would change what the commit sees after this check), joined by `&&`. Anything the shell could read differently from shlex (other commands, ; | ( ` newline,
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
        elif set(token) <= _OPERATORS:  # shlex with punctuation_chars yields these as tokens
            return None
        else:
            segments[-1].append(token)
    where = cwd
    for words in segments[:-1]:
        words = _unwrap(words)
        if words[:1] and _is_command(words[0], "git") and _git_subcommand(words) in _SAFE_GIT:
            continue
        if len(words) != 2 or words[0] != "cd" or words[1].startswith("-"):
            return None
        if os.environ.get("CDPATH") and not words[1].startswith(("/", ".")):
            return None
        where = Path(os.path.normpath(where / words[1]))  # logical, like the shell's cd
        if not where.is_dir():
            return None
    words = segments[-1]
    while words and re.fullmatch(r"\w+=.*", words[0]):
        if words[0].startswith("GIT_"):
            return None
        words = words[1:]
    words = _unwrap(words)
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


def _unwrap(words: list[str]) -> list[str]:
    """`rtk [-opts] [proxy [-opts]] git ...` -> `git ...`. Only before git: `rtk proxy cd x` runs cd in a child
    process, so it must not move where the commit is judged."""
    if not words or not _is_command(words[0], "rtk"):
        return words
    i = _skip_options(words, 1)
    if words[i : i + 1] == ["proxy"]:
        i = _skip_options(words, i + 1)
    return words[i:] if i < len(words) and _is_command(words[i], "git") else words


def _is_command(word: str, name: str) -> bool:
    """`git` or `/abs/path/git`; a relative `./tools/git` may be the agent's own script."""
    return word == name or (word.startswith("/") and Path(word).name == name)


def _skip_options(words: list[str], i: int) -> int:
    while i < len(words) and words[i].startswith("-"):
        i += 1
    return i


def _git_subcommand(words: list[str]) -> str | None:
    """`git [-C dir]... <sub>` -> sub; None with any other global option before it."""
    i = 1
    while words[i : i + 1] == ["-C"]:
        i += 2
    return words[i] if i < len(words) else None


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
