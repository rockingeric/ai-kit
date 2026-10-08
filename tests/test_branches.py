import json

from aikit import build, doctor, records
from aikit.core import current_branch, load_project
from aikit.hook import pre_bash
from conftest import git


def _bash(project, command):
    return pre_bash(json.dumps({"cwd": str(project.root), "tool_input": {"command": command}}))


def _approvable(project, title):
    path = records.new_wish(project, title)
    path.write_text(path.read_text().replace("## Critérios de aceite\n- [ ] ", "## Critérios de aceite\n- [ ] Funciona"))
    return path


def test_branch_is_created_on_approval_not_on_creation(project):
    _approvable(project, "Migrar auth para JWT")
    assert current_branch(project.root) == "main"
    _, note = records.approve_wish(project, "migrar-auth-para-jwt")
    assert current_branch(project.root) == "wish/migrar-auth-para-jwt"
    assert "criada" in note


def test_approval_respects_enforce_false(project):
    cfg = project.ai / "project.yaml"
    cfg.write_text(cfg.read_text() + "git:\n  enforce_branches: false\n")
    project = load_project(project.root)
    _approvable(project, "Sem branch")
    _, note = records.approve_wish(project, "sem-branch")
    assert note is None and current_branch(project.root) == "main"


def test_agent_cannot_accept_adr_or_approve_wish(project, capsys):
    git(project.root, "switch", "-q", "-c", "feat/x")  # off main: only the human-only rule applies
    assert _bash(project, "aikit adr accept 0003") == 2
    assert "decisão do humano" in capsys.readouterr().err
    assert _bash(project, "cd x && .venv/bin/aikit wish approve jwt") == 2
    assert _bash(project, "aikit adr new 'x' && aikit lint") == 0
    assert _bash(project, "echo 'rode aikit wish approve jwt'") == 0  # a mention is fine


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
