"""Wish worktrees (ADR-0023): `wt-<initials>-<slug>` next to the repo, kit symlinked in."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from aikit.core import (
    AI_DIR,
    AikitError,
    Project,
    current_branch,
    git,
    is_tracked,
    load_project,
    write_if_changed,
)

SETTINGS = ".claude/settings.local.json"


def main_root(project: Project) -> Path:
    """The main checkout, also when `project` was loaded from a linked worktree."""
    listed = list(_listing(project.root))  # git lists the main worktree first
    return listed[0][0] if listed else project.root


def initials(name: str) -> str:
    parts = [p for p in re.split(r"[-_. ]+", name) if p]
    return "".join(p[0] for p in parts).lower() or "x"


def target(project: Project, slug: str) -> Path:
    main = main_root(project)
    configured = (project.config.get("git") or {}).get("worktree_dir")
    if configured:
        parent = Path(configured).expanduser()
        parent = parent if parent.is_absolute() else main / parent
    else:
        parent = main.parent  # next to the repo, in its workspace at any depth
    return parent.resolve() / f"wt-{initials(main.name)}-{slug}"


def _listing(root: Path):
    """(path, branch or None) per worktree. -z: a newline in a path cannot fake a `branch` line."""
    out = git(root, "worktree", "list", "--porcelain", "-z") or ""
    for record in out.split("\0\0"):
        fields = [f for f in record.split("\0") if f]
        if not fields or not fields[0].startswith("worktree "):
            continue
        branch = next((f.removeprefix("branch refs/heads/") for f in fields if f.startswith("branch refs/heads/")), None)
        yield Path(fields[0].removeprefix("worktree ")).resolve(), branch


def worktrees(root: Path) -> dict[str, Path]:
    """branch name -> worktree path, only for paths that really are that branch's checkout of this repo."""
    common = _common_dir(root)
    return {
        branch: path
        for path, branch in _listing(root)
        if branch and path.is_dir() and current_branch(path) == branch and _common_dir(path) == common
    }


def _common_dir(path: Path) -> Path | None:
    out = git(path, "rev-parse", "--path-format=absolute", "--git-common-dir")
    return Path(out).resolve() if out else None


def ensure(project: Project, slug: str) -> str | None:
    """Open `wish/<slug>` in its worktree, creating or reusing it. Returns a note, or None if off."""
    if not project.enforce_branches or git(project.root, "rev-parse", "--git-dir") is None:
        return None
    branch = f"wish/{slug}"
    main = main_root(project)
    git(main, "worktree", "prune")  # forget worktrees deleted by hand, so they are recreated
    path = worktrees(main).get(branch)
    if path == main:
        return f"branch {branch} já está no checkout principal ({main}); nenhum worktree criado"
    if path:
        state = "já existia"
    else:
        path = target(project, slug)
        if path.exists() or path.is_symlink():
            raise AikitError(f"{path} já existe e não é worktree de {branch}; mude git.worktree_dir")
        exists = git(main, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}") is not None
        args = ["worktree", "add", str(path), branch] if exists else ["worktree", "add", "-b", branch, str(path)]
        try:
            subprocess.run(["git", *args], cwd=main, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as exc:
            raise AikitError(f"não consegui criar o worktree {path}: {exc.stderr.strip()}") from exc
        state = "criado"
    provision(main, path)
    return f"worktree {path} ({state}) na branch {branch}; abra uma sessão nele: cd {path} && claude"


def _inside(wt: Path, dst: Path) -> None:
    """Refuse when a folder between the worktree and `dst` is a symlink the branch brought in:
    following it would write outside the worktree (e.g. a committed `.claude` -> ~/.claude)."""
    for parent in dst.relative_to(wt).parents:
        if (wt / parent).is_symlink():
            raise AikitError(f"{wt / parent} é symlink versionado na branch; não provisiono o worktree através dele")


def _link(src: Path, dst: Path, wt: Path) -> None:
    _inside(wt, dst)
    if dst.exists() or dst.is_symlink():  # already linked, or tracked: leave it
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.symlink_to(src)


def provision(main: Path, wt: Path) -> None:
    """Symlink the excluded kit files into the worktree; index.yaml is built there, per branch."""
    linked_ai = (main / AI_DIR).is_dir() and not is_tracked(main, AI_DIR)
    if linked_ai and (is_tracked(wt, AI_DIR) or (wt / AI_DIR).is_symlink()):
        # The kit's config must come from the main checkout, not from what the branch committed.
        raise AikitError(f"a branch versiona {AI_DIR}/ e o projeto não; tire {AI_DIR}/ da branch antes de abrir o worktree")
    if linked_ai:
        # A real folder: the `/.ai/` exclude pattern only matches directories, not a symlink.
        (wt / AI_DIR).mkdir(exist_ok=True)
        for item in (main / AI_DIR).iterdir():
            if item.name != "index.yaml":
                _link(item, wt / AI_DIR / item.name, wt)
    manifest = load_project(main).manifest()
    for rel in [*manifest.get("files", []), SETTINGS]:
        src = main / rel
        if not rel.startswith(f"{AI_DIR}/") and src.is_file() and not is_tracked(main, rel):
            _link(src, wt / rel, wt)
    if linked_ai and (wt / AI_DIR / "project.yaml").is_file():  # a tracked index is the branch's own
        from aikit import build  # build imports core; keep worktree importable on its own

        project = load_project(wt)
        index = project.ai / "index.yaml"
        _inside(wt, index)
        if index.is_symlink():
            raise AikitError(f"{index} é symlink; não escrevo o índice através dele")
        write_if_changed(index, build.plan(project).writes[index])


def find(project: Project, slug: str) -> Path | None:
    """The wish's linked worktree; None when it has none or it is the main checkout."""
    main = main_root(project)
    path = worktrees(main).get(f"wish/{slug}")
    return path if path and path != main else None


def is_clean(path: Path) -> bool:
    return git(path, "status", "--porcelain") == ""


def remove(project: Project, path: Path) -> None:
    """Never --force: git refuses a worktree with changes."""
    try:
        subprocess.run(
            ["git", "worktree", "remove", str(path)],
            cwd=main_root(project), capture_output=True, text=True, check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise AikitError(f"não consegui remover o worktree {path}: {exc.stderr.strip()}") from exc
