"""Delimited, idempotent block in .git/info/exclude (never touches the team's .gitignore)."""

from __future__ import annotations

import re
from pathlib import Path

from aikit.core import git

START = "# >>> ai-kit (gerenciado por `aikit`; não edite este bloco)"
END = "# <<< ai-kit"
_BLOCK_RE = re.compile(r"\n?^# >>> ai-kit.*?^# <<< ai-kit[^\n]*\n?", re.S | re.M)


def exclude_file(root: Path) -> Path | None:
    out = git(root, "rev-parse", "--git-path", "info/exclude")
    if not out:
        return None
    path = Path(out)
    return path if path.is_absolute() else root / path


def read_block(root: Path) -> list[str] | None:
    path = exclude_file(root)
    if not path or not path.is_file():
        return None
    m = _BLOCK_RE.search(path.read_text(encoding="utf-8"))
    if not m:
        return None
    return [line for line in m.group(0).splitlines() if line and not line.startswith("#")]


def write_block(root: Path, entries: list[str]) -> bool:
    path = exclude_file(root)
    if not path:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    current = path.read_text(encoding="utf-8") if path.is_file() else ""
    base = _BLOCK_RE.sub("\n", current).rstrip("\n")
    block = "\n".join([START, *entries, END])
    path.write_text((base + "\n\n" if base else "") + block + "\n", encoding="utf-8")
    return True


def remove_block(root: Path) -> None:
    path = exclude_file(root)
    if not path or not path.is_file():
        return
    current = path.read_text(encoding="utf-8")
    cleaned = _BLOCK_RE.sub("\n", current).rstrip("\n")
    path.write_text(cleaned + "\n" if cleaned else "", encoding="utf-8")
