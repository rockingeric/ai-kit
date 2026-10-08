import pytest
import yaml

from aikit import build, lint, records, schemas
from aikit.core import AikitError, body_sha, load_yaml, parse_doc


def _meta(path):
    return parse_doc(path).meta


def test_adr_new_numbers_and_validates(project):
    first = records.new_adr(project, "Usar Postgres", ["db"], "Postgres como banco")
    second = records.new_adr(project, "Fila com SQS")
    assert first.name == "ADR-0001-usar-postgres.md"
    assert second.name == "ADR-0002-fila-com-sqs.md"
    meta = _meta(first)
    assert meta["status"] == "proposed" and meta["date"] == "2026-10-08"
    assert schemas.errors("adr-frontmatter", meta) == []
    assert "date: 2026-10-08" in first.read_text()  # unquoted


def test_supersede_updates_both_files_and_index(project):
    old = records.new_adr(project, "Prisma como ORM")
    records.accept(project, "1")
    new = records.new_adr(project, "Drizzle no lugar de Prisma", supersedes="0001")
    build.run(project)
    assert _meta(old)["status"] == "superseded"
    assert _meta(old)["superseded_by"] == "ADR-0002"
    assert _meta(new)["supersedes"] == "ADR-0001"
    index = load_yaml(project.ai / "index.yaml")
    assert index["decisions_dir"] == "docs/decisions"
    assert index["decisions"][0] == {"id": "ADR-0002", "status": "proposed", "summary": "Drizzle no lugar de Prisma"}
    assert index["decisions"][1] == {"id": "ADR-0001", "status": "superseded"}
    assert lint.run(project).errors == []


def test_accept_freezes_body_and_lint_catches_tampering(project):
    path = records.new_adr(project, "Monorepo")
    _, changed = records.accept(project, "ADR-0001")
    assert changed
    meta = _meta(path)
    assert meta["status"] == "accepted"
    assert meta["body_sha"] == body_sha(parse_doc(path).body)
    assert lint.run(project).errors == []

    path.write_text(path.read_text() + "\nmudança depois do aceite\n")
    errors = lint.run(project).errors
    assert any("body_sha não bate" in e for e in errors)
    with pytest.raises(AikitError, match="imutável"):
        records.accept(project, "1")


def test_lint_rejects_accepted_without_sha(project):
    path = records.new_adr(project, "Sem sha")
    text = path.read_text().replace("status: proposed", "status: accepted")
    path.write_text(text)
    assert any("accepted sem body_sha" in e for e in lint.run(project).errors)


def test_status_transitions(project):
    records.new_adr(project, "A")
    records.new_adr(project, "B", supersedes="1")
    with pytest.raises(AikitError, match="superseded"):
        records.accept(project, "1")
    records.new_adr(project, "C")
    records.reject(project, "3")
    with pytest.raises(AikitError, match="só proposed"):
        records.reject(project, "3")


def test_summary_is_capped_at_80_chars(project):
    path = records.new_adr(project, "x" * 120)
    assert len(_meta(path)["summary"]) == 80
    assert lint.run(project).errors == []


def test_runbook_new_and_staleness(project, monkeypatch):
    path = records.new_runbook(project, "Reverter deploy", "5xx após deploy", ["deploy"])
    meta = _meta(path)
    assert meta["id"] == "RB-reverter-deploy" and meta["last_verified"] == "2026-10-08"
    assert "type" not in meta  # implied by the folder
    assert lint.run(project).warnings == []

    monkeypatch.setenv("AIKIT_TODAY", "2027-03-01")
    assert any("last_verified há 144 dias" in w for w in lint.run(project).warnings)
    records.verify_runbook(project, "reverter-deploy")
    assert _meta(path)["last_verified"] == "2027-03-01"


def test_adr_template_frontmatter_is_plain_yaml(project):
    path = records.new_adr(project, "Título: com dois pontos")
    raw = path.read_text().split("---")[1]
    assert yaml.safe_load(raw)["title"] == "Título: com dois pontos"
