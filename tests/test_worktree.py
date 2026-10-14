import json

import pytest

from aikit import records, worktree
from aikit.core import AikitError, current_branch, load_project
from aikit.hook import pre_bash
from conftest import git


def _with_worktrees(project, where):
    cfg = project.ai / "project.yaml"
    cfg.write_text(cfg.read_text() + f"git:\n  worktrees: true\n  worktree_dir: {where}\n")
    return load_project(project.root)


def _approvable(project, title):
    path = records.new_wish(project, title)
    path.write_text(path.read_text().replace("## Critérios de aceite\n- [ ] ", "## Critérios de aceite\n- [ ] Funciona"))
    return path


def _bash(cwd, command):
    return pre_bash(json.dumps({"cwd": str(cwd), "tool_input": {"command": command}}))


def test_initials_and_default_place():
    assert worktree.initials("ai-kit") == "ak"
    assert worktree.initials("my_app.web site") == "maws"
    assert worktree.initials("--") == "x"


def test_default_target_is_outside_the_projects_folder(project):
    assert worktree.target(project, "jwt") == project.root.parent.parent / "wt-p-jwt"


def test_approve_opens_a_provisioned_worktree(project, tmp_path):
    project = _with_worktrees(project, tmp_path)
    _approvable(project, "Migrar auth")
    _, note = records.approve_wish(project, "migrar-auth")
    wt = tmp_path / "wt-p-migrar-auth"
    assert f"cd {wt} && claude" in note and "criado" in note
    assert current_branch(project.root) == "main"
    assert current_branch(wt) == "wish/migrar-auth"
    ai = wt / ".ai"
    assert ai.is_dir() and not ai.is_symlink()
    assert (ai / "project.yaml").is_symlink() and (ai / "wishes").is_symlink()
    assert (ai / "index.yaml").is_file() and not (ai / "index.yaml").is_symlink()
    assert (wt / "CLAUDE.md").is_symlink()
    assert (wt / ".claude/agents/aikit-architect.md").is_symlink()
    assert (wt / ".claude/settings.local.json").is_symlink()
    assert git(wt, "status", "--porcelain") == ""  # the links are excluded like the originals
    wish = (ai / "wishes/migrar-auth.md").read_text()
    assert "status: approved" in wish  # one source: the approval shows in the worktree


def test_worktree_is_reused_and_existing_branch_is_checked_out(project, tmp_path):
    project = _with_worktrees(project, tmp_path)
    assert "criado" in worktree.ensure(project, "a")
    assert "já existia" in worktree.ensure(project, "a")
    git(project.root, "branch", "wish/b")
    worktree.ensure(project, "b")
    assert current_branch(tmp_path / "wt-p-b") == "wish/b"


def test_occupied_path_is_an_error_never_overwritten(project, tmp_path):
    project = _with_worktrees(project, tmp_path)
    (tmp_path / "wt-p-c").mkdir()
    (tmp_path / "wt-p-c" / "keep.txt").write_text("x")
    with pytest.raises(AikitError, match="já existe"):
        worktree.ensure(project, "c")
    assert (tmp_path / "wt-p-c" / "keep.txt").read_text() == "x"


def test_worktree_respects_enforce_false(project, tmp_path):
    cfg = project.ai / "project.yaml"
    cfg.write_text(cfg.read_text() + f"git:\n  worktrees: true\n  worktree_dir: {tmp_path}\n  enforce_branches: false\n")
    assert worktree.ensure(load_project(project.root), "d") is None
    assert not (tmp_path / "wt-p-d").exists()


def test_session_in_worktree_has_the_kit_and_can_commit(project, tmp_path):
    project = _with_worktrees(project, tmp_path)
    worktree.ensure(project, "e")
    wt = tmp_path / "wt-p-e"
    assert load_project(wt).root == wt
    assert _bash(wt, "git commit -m x") == 0
    assert _bash(wt, "aikit wish approve e") == 2  # still human-only there
    assert _bash(project.root, "git commit -m x") == 2  # main stays protected


def test_clean_worktree_is_removed_without_touching_main(project, tmp_path):
    project = _with_worktrees(project, tmp_path)
    _approvable(project, "Fim")
    records.approve_wish(project, "fim")
    wt = worktree.find(project, "fim")
    assert wt == tmp_path / "wt-p-fim" and worktree.is_clean(wt)
    (wt / "novo.py").write_text("x")
    assert not worktree.is_clean(wt)
    with pytest.raises(AikitError):
        worktree.remove(project, wt)  # git refuses; no --force
    (wt / "novo.py").unlink()
    worktree.remove(project, wt)
    assert not wt.exists()
    assert (project.ai / "wishes/fim.md").is_file() and (project.ai / "project.yaml").is_file()
    assert "wish/fim" in git(project.root, "branch")  # the branch stays for the PR


def test_done_offers_removal_only_for_a_clean_worktree(project, tmp_path, capsys):
    from aikit.cli import main

    project = _with_worktrees(project, tmp_path)
    for slug in ("limpo", "sujo"):
        _approvable(project, slug.capitalize())
        records.approve_wish(project, slug)
    (tmp_path / "wt-p-sujo" / "wip.py").write_text("x")
    main(["wish", "done", "limpo"])
    main(["wish", "done", "sujo"])
    out = capsys.readouterr().out
    assert f"git worktree remove {tmp_path / 'wt-p-limpo'}" in out  # no tty: says how, removes nothing
    assert "wt-p-sujo tem mudanças não commitadas; mantido" in out
    assert (tmp_path / "wt-p-limpo").is_dir() and (tmp_path / "wt-p-sujo").is_dir()
