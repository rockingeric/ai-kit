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


def _worktree(project, tmp_path, branch):
    path = tmp_path / f"wt-{branch.replace('/', '-')}"
    git(project.root, "worktree", "add", "-q", "-b", branch, str(path))
    return path.resolve()


def test_commit_is_judged_where_it_runs(project, tmp_path):
    feature = _worktree(project, tmp_path, "fix/y")  # no .ai/ there: it is excluded, not tracked
    assert _bash(project, f"cd {feature} && git commit -m x") == 0
    assert _bash(project, f"git -C {feature} commit -m x") == 0
    assert _bash(project, f"cd {feature.parent} && git -C {feature.name} add . && git -C {feature.name} commit -m x") == 0
    git(project.root, "switch", "-q", "-c", "feat/z")
    git(feature, "switch", "-q", "main")
    assert _bash(project, f"cd {feature} && git commit -m x") == 2
    assert _bash(project, f"git -C {feature} commit -m x") == 2
    assert _bash(project, "git commit -m x") == 0


def test_commit_in_unrelated_repo_is_not_judged(project, tmp_path):
    other = tmp_path / "outro"
    other.mkdir()
    git(other, "init", "-q", "-b", "main")
    assert _bash(project, f"cd {other} && git commit -m x") == 0
    assert _bash(project, f'cd "{other}" && git add . && git -c user.name=a commit -m x') == 0


def test_ambiguous_dir_falls_back_to_session_cwd(project, tmp_path):
    elsewhere = tmp_path / "fora"
    elsewhere.mkdir()
    for command in [
        f"(cd {elsewhere}); git commit -m x",  # subshell: the cd does not reach the commit
        f"cd {elsewhere}; git commit -m x",
        f"cd {elsewhere};git commit -m x",
        f'echo "a && cd {elsewhere}" && git commit -m x',
        f"cd {elsewhere} || git commit -m x",
        f"cd /nao/existe && git commit -m x",
        f"cd {elsewhere} && cd - && git commit -m x",
        f"cd {elsewhere} && cd $OLDPWD && git commit -m x",
        f"pushd {elsewhere} && popd && git commit -m x",
        f"cd {elsewhere}\ngit commit -m x",
        f"cd {elsewhere} && git --git-dir={project.root}/.git --work-tree={project.root} commit -m x",
        f"cd {elsewhere} && GIT_DIR={project.root}/.git git commit -m x",
        f"export GIT_DIR={project.root}/.git && cd {elsewhere} && git commit -m x",
        f"cd {elsewhere} && builtin cd {project.root} && git commit -m x",
        f"cd {elsewhere} && eval cd {project.root} && git commit -m x",
        f"cd {elsewhere} && source volta.sh && git commit -m x",
        f"cd {elsewhere} && X=1 cd {project.root} && git commit -m x",
        f"cd '~' && git commit -m x",  # quoted ~ is a literal dir for the shell
        f"git -C {elsewhere}#x commit -m x",  # mid-word # is literal for the shell
    ]:
        assert _bash(project, command) == 2, command


def test_config_in_a_subfolder_does_not_disable_the_guard(project):
    sub = project.root / "sub" / ".ai"
    sub.mkdir(parents=True)
    (sub / "project.yaml").write_text("name: x\ngit:\n  enforce_branches: false\n")
    assert _bash(project, "cd sub && git commit -m x") == 2


def test_cd_through_a_link_is_logical_like_the_shell(project, tmp_path):
    outside = tmp_path / "fora" / "alvo"
    outside.mkdir(parents=True)
    (project.root / "lnk").symlink_to(outside)
    assert _bash(project, "cd lnk/.. && git commit -m x") == 2  # the shell is back in the repo
