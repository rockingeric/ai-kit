"""PostToolUse hook: rebuild when the agent edits .ai/ or the project's docs."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from aikit import build
from aikit.core import AikitError, load_project

GENERATED = {"index.yaml", "manifest.json"}


def watched(project, path: Path) -> bool:
    if path.name in GENERATED and path.parent == project.ai:
        return False
    roots = [project.ai, project.path("docs"), project.path("adr"), project.path("runbooks")]
    return any(path == r or r in path.parents for r in roots)


def post_edit(stdin: str) -> int:
    """Exit 0 = silent; exit 2 = stderr goes back to Claude (PostToolUse cannot block)."""
    try:
        payload = json.loads(stdin or "{}")
    except json.JSONDecodeError:
        return 0
    file_path = (payload.get("tool_input") or {}).get("file_path")
    cwd = payload.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    if not file_path:
        return 0
    try:
        project = load_project(Path(cwd), required=False)
        if not project.config:
            return 0
        path = Path(file_path)
        path = (path if path.is_absolute() else Path(cwd) / path).resolve()
        if not watched(project, path):
            return 0
        _, problems = build.run(project)
    except AikitError as exc:
        problems = [str(exc)]
    if problems:
        print("aikit build encontrou problemas:", *problems, sep="\n- ", file=sys.stderr)
        return 2
    return 0
