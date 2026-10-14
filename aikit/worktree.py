"""Wish worktrees (ADR-0022): `wt-<initials>-<slug>` outside the projects folder, kit symlinked in."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from aikit.core import AI_DIR, AikitError, Project, git, is_tracked, load_project, write_if_changed

SETTINGS = ".claude/settings.local.json"


def main_root(project: Project) -> Path:
    """The main checkout, also when `project` was loaded from a linked worktree."""
    out = git(project.root, "rev-parse", "--path-format=absolute", "--git-common-dir")
    common = Path(out).resolve() if out else None
    return common.parent if common and common.name == ".git" else project.root


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
        parent = main.parent.parent  # outside the folder that holds the projects
    return parent.resolve() / f"wt-{initials(main.name)}-{slug}"


def worktrees(root: Path) -> dict[str, Path]:
    """branch name -> worktree path, for every checkout of this repo."""
    out = git(root, "worktree", "list", "--porcelain") or ""
    found: dict[str, Path] = {}
    path: Path | None = None
    for line in out.splitlines():
        if line.startswith("worktree "):
            path = Path(line.removeprefix("worktree ")).resolve()
        elif line.startswith("branch refs/heads/") and path:
            found[line.removeprefix("branch refs/heads/")] = path
    return found


def ensure(project: Project, slug: str) -> str | None:
    """Open `wish/<slug>` in its worktree, creating or reusing it. Returns a note, or None if off."""
    if not project.enforce_branches or git(project.root, "rev-parse", "--git-dir") is None:
        return None
    branch = f"wish/{slug}"
    main = main_root(project)
    path = worktrees(main).get(branch)
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
    if path != main:
        provision(main, path)
    return f"worktree {path} ({state}) na branch {branch}; abra uma sessão nele: cd {path} && claude"


def _link(src: Path, dst: Path) -> None:
    if dst.exists() or dst.is_symlink():  # already linked, or tracked: leave it
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.symlink_to(src)


def provision(main: Path, wt: Path) -> None:
    """Symlink the excluded kit files into the worktree; index.yaml is built there, per branch."""
    if (main / AI_DIR).is_dir() and not is_tracked(main, AI_DIR):
        # A real folder: the `/.ai/` exclude pattern only matches directories, not a symlink.
        (wt / AI_DIR).mkdir(exist_ok=True)
        for item in (main / AI_DIR).iterdir():
            if item.name != "index.yaml":
                _link(item, wt / AI_DIR / item.name)
    manifest = load_project(main).manifest()
    for rel in [*manifest.get("files", []), SETTINGS]:
        src = main / rel
        if not rel.startswith(f"{AI_DIR}/") and src.is_file() and not is_tracked(main, rel):
            _link(src, wt / rel)
    if (wt / AI_DIR / "project.yaml").is_file():
        from aikit import build  # build imports core; keep worktree importable on its own

        project = load_project(wt)
        index = project.ai / "index.yaml"
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
