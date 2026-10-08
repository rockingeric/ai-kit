import json

import pytest

from aikit import backup, doctor, exclude, install
from aikit.core import AikitError, load_project
from aikit.hook import post_edit
from conftest import git


def _status(root):
    return git(root, "status", "--porcelain", "--untracked-files=all")


def test_init_keeps_git_status_clean_and_uninstall_restores(repo):
    before = _status(repo)
    install.init(repo, [])
    assert _status(repo) == before  # nothing kit-owned shows up; empty docs dirs are invisible to git
    assert (repo / "docs/decisions").is_dir() and (repo / "docs/runbooks").is_dir()
    assert (repo / "CLAUDE.md").read_text() == "@.ai/AGENTS.md\n"
    assert (repo / "AGENTS.md").is_symlink()
    assert len(list((repo / ".claude/agents").glob("aikit-*.md"))) == 5
    assert (repo / ".claude/skills/aikit-adr/SKILL.md").is_file()

    install.uninstall(repo, assume_yes=True)
    assert _status(repo) == before
    assert not (repo / ".ai").exists() and not (repo / ".claude").exists()
    assert not (repo / "CLAUDE.md").exists() and not (repo / "AGENTS.md").is_symlink()
    assert (repo / "docs/decisions").is_dir()
    assert exclude.read_block(repo) is None


def test_docs_survive_uninstall_and_are_versionable(repo):
    install.init(repo, [])
    from aikit import records

    records.new_adr(load_project(repo), "Decisão")
    assert "docs/decisions/ADR-0001-decisao.md" in _status(repo)
    install.uninstall(repo, assume_yes=True)
    assert (repo / "docs/decisions/ADR-0001-decisao.md").is_file()


def test_init_is_idempotent(repo):
    install.init(repo, [])
    first = exclude.exclude_file(repo).read_text()
    assert "/.genie/" not in first
    settings = (repo / ".claude/settings.local.json").read_text()
    install.init(repo, [])
    assert exclude.exclude_file(repo).read_text() == first
    assert first.count("# >>> ai-kit") == 1
    assert (repo / ".claude/settings.local.json").read_text() == settings


def test_tracked_claude_md_is_not_touched(repo):
    (repo / "CLAUDE.md").write_text("# Regras do time\n")
    git(repo, "add", "CLAUDE.md")
    git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "team")
    notes = install.init(repo, [])
    assert (repo / "CLAUDE.md").read_text() == "# Regras do time\n"
    assert (repo / "CLAUDE.local.md").read_text() == "@.ai/AGENTS.md\n"
    assert any("CLAUDE.local.md" in n for n in notes)
    assert _status(repo) == ""
    install.uninstall(repo, assume_yes=True)
    assert not (repo / "CLAUDE.local.md").exists()
    assert (repo / "CLAUDE.md").read_text() == "# Regras do time\n"


def test_untracked_claude_md_gets_import_line_and_loses_it_on_uninstall(repo):
    (repo / "CLAUDE.md").write_text("minhas notas\n")
    install.init(repo, [])
    assert (repo / "CLAUDE.md").read_text() == "minhas notas\n\n@.ai/AGENTS.md\n"
    install.uninstall(repo, assume_yes=True)
    assert (repo / "CLAUDE.md").read_text() == "minhas notas\n"


def test_existing_settings_are_merged_not_overwritten(repo):
    claude = repo / ".claude"
    claude.mkdir()
    existing = {"permissions": {"allow": ["Bash(ls)"]}, "hooks": {"PostToolUse": [{"matcher": "Bash", "hooks": []}]}}
    (claude / "settings.local.json").write_text(json.dumps(existing))
    install.init(repo, [])
    merged = json.loads((claude / "settings.local.json").read_text())
    assert merged["permissions"] == existing["permissions"]
    assert len(merged["hooks"]["PostToolUse"]) == 2
    install.uninstall(repo, assume_yes=True)
    assert json.loads((claude / "settings.local.json").read_text()) == existing


def test_uninstall_requires_backup_or_yes(repo, tmp_path):
    install.init(repo, [])
    with pytest.raises(AikitError, match="backup"):
        install.uninstall(repo, assume_yes=False)
    backup.set_dir(tmp_path / "bkp")
    notes = install.uninstall(repo, assume_yes=False)
    assert any("backup" in n for n in notes)
    assert (tmp_path / "bkp/proj/project.yaml").is_file()


def test_backup_records_date_and_doctor_tracks_age(project, tmp_path, monkeypatch):
    problems, warnings = doctor.run(project)
    assert problems == []
    assert any("nunca teve backup" in w for w in warnings)
    assert any("TODO" in w for w in warnings)
    target = backup.run(project, tmp_path / "bkp")
    assert (target / "AGENTS.md").is_file() and not (target / "index.yaml").exists()
    assert not any("backup" in w for w in doctor.run(project)[1])
    monkeypatch.setenv("AIKIT_TODAY", "2026-10-20")
    assert any("último backup há 12 dias" in w for w in doctor.run(project)[1])


def test_doctor_flags_stale_build(project):
    (project.ai / "personas" / "qa.yaml").write_text("model: haiku\n")
    problems, _ = doctor.run(project)
    assert any("build desatualizado" in p for p in problems)


def test_unknown_overlay_is_rejected(repo):
    with pytest.raises(AikitError, match="overlay"):
        install.init(repo, ["nao-existe"])


def _hook(project, rel):
    payload = {"cwd": str(project.root), "tool_input": {"file_path": str(project.root / rel)}}
    return post_edit(json.dumps(payload))


def test_hook_rebuilds_when_override_changes(project):
    (project.ai / "personas" / "architect.yaml").write_text("principles:\n  - Regra nova\n")
    assert _hook(project, ".ai/personas/architect.yaml") == 0
    assert "Regra nova" in (project.root / ".claude/agents/aikit-architect.md").read_text()


def test_hook_ignores_files_outside_ai_and_docs(project):
    (project.ai / "personas" / "architect.yaml").write_text("principles:\n  - Regra nova\n")
    assert _hook(project, "app.py") == 0
    assert "Regra nova" not in (project.root / ".claude/agents/aikit-architect.md").read_text()


def test_hook_reports_problems_to_claude_with_exit_2(project, capsys):
    (project.ai / "personas" / "qa.yaml").write_text("model: gpt\n")
    assert _hook(project, ".ai/personas/qa.yaml") == 2
    assert ".ai/personas/qa.yaml" in capsys.readouterr().err
