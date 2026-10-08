import yaml

from aikit import build, schemas
from aikit.compile_personas import compile_persona
from aikit.core import parse_doc
from aikit.lint import PERSONA_MAX_LINES
from aikit.merge import merge, resolve


def test_merge_lists_add_scalars_replace_dicts_merge():
    base = {"model": "opus", "tools": ["Read", "Grep"], "outputs": {"adr": "a"}, "role": "x"}
    layer = {"model": "sonnet", "tools": ["Grep", "Write"], "outputs": {"doc": "d"}}
    out = merge(base, layer)
    assert out["model"] == "sonnet"
    assert out["tools"] == ["Read", "Grep", "Write"]
    assert out["outputs"] == {"adr": "a", "doc": "d"}
    assert out["role"] == "x"


def test_kit_personas_are_valid_and_within_budget(project):
    personas, problems = resolve(project)
    assert problems == []
    assert [p.id for p in personas] == ["architect", "qa", "reviewer", "security", "tech-writer"]
    for persona in personas:
        assert schemas.errors("persona", persona.data) == []
        assert compile_persona(persona, project).count("\n") <= PERSONA_MAX_LINES


def test_compiled_frontmatter_is_valid_for_claude_code(project):
    personas, _ = resolve(project)
    architect = next(p for p in personas if p.id == "architect")
    text = compile_persona(architect, project)
    doc_meta = yaml.safe_load(text.split("---")[1])
    assert doc_meta["name"] == "aikit-architect"
    assert doc_meta["model"] == "opus"
    assert doc_meta["tools"] == "Read, Grep, Glob, Bash, Write, Edit"
    assert "\n" not in doc_meta["description"]
    assert "aikit:generated" in text
    # `reads` becomes an explicit instruction, limited to the declared sections
    assert "`docs.explanation`" in text and "`docs.how-to`" not in text
    assert "docs/decisions/ADR-NNNN-slug.md" in text


def test_overlay_then_project_override(project):
    (project.ai / "overlays.yaml").write_text("- _example\n")
    (project.ai / "personas" / "security.yaml").write_text(
        "model: sonnet\nnever:\n  - Regra local\n"
    )
    personas, problems = resolve(project)
    assert problems == []
    security = next(p for p in personas if p.id == "security")
    assert security.data["model"] == "sonnet"
    assert any("Exemplo de overlay" in x for x in security.data["principles"])
    assert security.data["never"][-1] == "Regra local"
    assert security.sources == [
        "kit:personas/security.yaml",
        "kit:overlays/_example/personas/security.yaml",
        ".ai/personas/security.yaml",
    ]


def test_disabled_persona_is_removed_from_agents(project):
    (project.ai / "personas" / "qa.yaml").write_text("enabled: false\n")
    changed, problems = build.run(project)
    assert problems == []
    assert not (project.root / ".claude/agents/aikit-qa.md").exists()
    assert "aikit-qa" not in (project.ai / "AGENTS.md").read_text()
    assert ".claude/agents/aikit-qa.md" not in project.manifest()["files"]


def test_invalid_override_is_reported_once_and_skipped(project):
    (project.ai / "personas" / "qa.yaml").write_text("model: gpt\n")
    _, problems = build.run(project)
    assert len(problems) == 1 and problems[0].startswith(".ai/personas/qa.yaml")
    meta = parse_doc(project.root / ".claude/agents/aikit-architect.md").meta
    assert meta["name"] == "aikit-architect"
