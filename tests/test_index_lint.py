from aikit import build, lint, records, schemas
from aikit.core import load_yaml


def test_index_groups_docs_by_folder_type(project):
    records.new_runbook(project, "Rollback")
    arch = project.root / "docs/architecture"
    arch.mkdir()
    (arch / "overview.md").write_text("# Visão geral\n\nTexto.\n")
    ref = project.root / "docs/reference"
    ref.mkdir()
    (ref / "env.md").write_text("---\nsummary: Variáveis de ambiente\n---\nconteúdo\n")
    notes = project.ai / "docs"
    notes.mkdir()
    (notes / "spike.md").write_text("---\ntype: explanation\nsummary: Spike de cache\n---\n")
    build.run(project)

    index = load_yaml(project.ai / "index.yaml")
    assert schemas.errors("index", index) == []
    assert [d["path"] for d in index["docs"]["explanation"]] == [
        "docs/architecture/overview.md",
        ".ai/docs/spike.md",
    ]
    assert index["docs"]["explanation"][0]["summary"] == "Visão geral"
    assert index["docs"]["reference"] == [{"path": "docs/reference/env.md", "summary": "Variáveis de ambiente"}]
    assert index["docs"]["how-to"][0]["id"] == "RB-rollback"
    assert "tutorial" not in index["docs"]  # empty groups are omitted
    assert "last_verified: 2026-10-08" in (project.ai / "index.yaml").read_text()


def test_generated_date_only_changes_with_content(project, monkeypatch):
    before = (project.ai / "index.yaml").read_text()
    monkeypatch.setenv("AIKIT_TODAY", "2026-12-01")
    changed, _ = build.run(project)
    assert changed == []
    assert (project.ai / "index.yaml").read_text() == before
    records.new_adr(project, "Algo novo")
    build.run(project)
    assert "generated: 2026-12-01" in (project.ai / "index.yaml").read_text()


def test_open_plans_are_indexed_and_done_plans_leave(project):
    records.new_plan(project, "Migrar auth para JWT", "JWT com refresh")
    draft, _ = records.new_plan(project, "Cache de catálogo")
    draft.write_text(draft.read_text().replace("status: active", "status: draft"))
    build.run(project)
    assert load_yaml(project.ai / "index.yaml")["plans"] == [
        {"path": ".ai/plans/migrar-auth-para-jwt.md", "status": "active", "summary": "JWT com refresh"},
        {"path": ".ai/plans/cache-de-catalogo.md", "status": "draft", "summary": "Cache de catálogo"},
    ]
    assert lint.run(project).errors == []

    path, open_items = records.finish_plan(project, "migrar-auth-para-jwt")
    assert open_items == []  # template has an empty criterion line, not a real one
    path.write_text(path.read_text().replace("status: done", "status: active").replace(
        "## Critérios de aceite\n- [ ] ", "## Critérios de aceite\n- [ ] Login devolve JWT\n- [x] Refresh rotaciona"))
    _, open_items = records.finish_plan(project, "PL-migrar-auth-para-jwt")
    assert open_items == ["Login devolve JWT"]
    build.run(project)
    plans = load_yaml(project.ai / "index.yaml")["plans"]
    assert [p["status"] for p in plans] == ["draft"]


def test_lint_checks_plan_frontmatter_and_adr_links(project):
    path, _ = records.new_plan(project, "Plano")
    path.write_text(path.read_text().replace("adrs: []", "adrs: [ADR-0009]").replace("status: active", "status: doing"))
    errors = lint.run(project).errors
    assert any("status" in e for e in errors)
    assert any("ADR-0009, que não existe" in e for e in errors)


def test_lint_diataxis_rules(project):
    notes = project.ai / "docs"
    notes.mkdir()
    (notes / "solta.md").write_text("# Sem tipo\n")
    guides = project.root / "docs/guides"
    guides.mkdir()
    (guides / "setup.md").write_text("---\ntype: reference\n---\n# Setup\n")
    errors = lint.run(project).errors
    assert any(".ai/docs/solta.md" in e and "type" in e for e in errors)
    assert any("docs/guides/setup.md" in e and "contradiz a pasta (tutorial)" in e for e in errors)


def test_lint_budgets(project):
    agents_md = project.ai / "AGENTS.md"
    agents_md.write_text(agents_md.read_text() + "linha\n" * 60)
    assert any("AGENTS.md" in w and "orçamento é 60" in w for w in lint.run(project).warnings)


def test_lint_refs_finds_dead_paths(project):
    arch = project.root / "docs/architecture"
    arch.mkdir()
    (arch / "overview.md").write_text(
        "# V\n\nVer `app.py`, `src/sumiu.py`, `npm test` e `paths.adr`.\n\n```\n`ignorado/no/bloco.py`\n```\n"
    )
    warnings = lint.run(project, refs=True).warnings
    assert warnings == ["docs/architecture/overview.md: cita `src/sumiu.py`, que não existe"]
