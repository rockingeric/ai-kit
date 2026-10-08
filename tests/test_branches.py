import json

from aikit import build, doctor, records
from aikit.core import current_branch, load_project
from aikit.hook import pre_bash
from conftest import git


def _bash(project, command):
    return pre_bash(json.dumps({"cwd": str(project.root), "tool_input": {"command": command}}))


def test_plan_new_creates_and_switches_to_its_branch(project):
    path, note = records.new_plan(project, "Migrar auth para JWT")
    assert current_branch(project.root) == "plan/migrar-auth-para-jwt"
    assert "criada" in note
    git(project.root, "switch", "-q", "main")
    path.unlink()
    _, note = records.new_plan(project, "Migrar auth para JWT")
    assert current_branch(project.root) == "plan/migrar-auth-para-jwt"
    assert "já existia" in note


def test_plan_new_respects_enforce_false(project):
    cfg = project.ai / "project.yaml"
    cfg.write_text(cfg.read_text() + "git:\n  enforce_branches: false\n")
    _, note = records.new_plan(load_project(project.root), "Sem branch")
    assert note is None and current_branch(project.root) == "main"


def test_commit_on_default_branch_is_blocked(project, capsys):
    assert _bash(project, 'git commit -m "x"') == 2
    assert "branch padrão (main)" in capsys.readouterr().err
    assert _bash(project, "git add . && git -C sub commit -am x") == 2
    assert _bash(project, "git --no-pager commit") == 2


def test_other_commands_and_branches_pass(project):
    assert _bash(project, "git status && git log --oneline") == 0
    assert _bash(project, "git commit-tree abc") == 0
    assert _bash(project, "echo 'rode git commit depois'") == 0  # a mention is not a commit
    assert _bash(project, "cat <<'EOF'\nuse `git commit` aqui\nEOF") == 0
    assert _bash(project, "GIT_AUTHOR_NAME=x git commit -m y") == 2
    assert _bash(project, "cd sub; git commit -m y") == 2
    git(project.root, "switch", "-q", "-c", "fix/bug")
    assert _bash(project, 'git commit -m "x"') == 0


def test_enforcement_can_be_disabled_and_default_branch_overridden(project):
    cfg = project.ai / "project.yaml"
    base = cfg.read_text()
    cfg.write_text(base + "git:\n  default_branch: trunk\n")
    assert _bash(project, "git commit -m x") == 0  # main is not the default anymore
    cfg.write_text(base + "git:\n  enforce_branches: false\n")
    assert _bash(project, "git commit -m x") == 0


def test_build_restores_missing_hooks(project):
    settings = project.root / ".claude/settings.local.json"
    data = json.loads(settings.read_text())
    assert set(data["hooks"]) == {"PostToolUse", "PreToolUse"}
    del data["hooks"]["PreToolUse"]
    settings.write_text(json.dumps(data))
    assert any("PreToolUse" in p for p in doctor.run(project)[0])
    build.run(project)
    assert "PreToolUse" in json.loads(settings.read_text())["hooks"]
    assert doctor.run(project)[0] == []
