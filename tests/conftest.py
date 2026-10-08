import subprocess
from pathlib import Path

import pytest

from aikit import install
from aikit.core import load_project


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    ).stdout


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.setenv("AIKIT_TODAY", "2026-10-08")
    monkeypatch.delenv("AIKIT_BACKUP_DIR", raising=False)
    monkeypatch.delenv("AIKIT_HOME", raising=False)


@pytest.fixture
def repo(tmp_path, monkeypatch) -> Path:
    root = tmp_path / "proj"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "init.defaultBranch", "main")  # local config beats the user's global one
    (root / "app.py").write_text("print('oi')\n")
    git(root, "add", ".")
    git(root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")
    monkeypatch.chdir(root)
    return root.resolve()


@pytest.fixture
def project(repo):
    install.init(repo, [])
    return load_project(repo)
