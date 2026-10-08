import pytest

from aikit import __version__
from aikit.cli import main
from aikit.core import Project, kit_root
from aikit.index_builder import collect
from aikit.lint import Report, _check_adrs


def test_version_and_help(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == f"aikit {__version__}"


def test_kit_own_adrs_are_valid():
    """Dogfooding: the kit's decisions live in docs/decisions and must pass the same lint."""
    project = Project(kit_root(), {"name": "ai-kit"})
    entries = [e for e in collect(project) if e.kind == "adr"]
    assert len(entries) == 18
    report = Report()
    _check_adrs(entries, report)
    assert report.errors == []
    superseded = {e.meta["id"]: e.meta["superseded_by"] for e in entries if e.meta["status"] == "superseded"}
    assert superseded == {"ADR-0004": "ADR-0014", "ADR-0005": "ADR-0015", "ADR-0011": "ADR-0016", "ADR-0012": "ADR-0017"}
