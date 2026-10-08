"""`aikit build`: merged personas -> subagents, AGENTS.md persona block, index.yaml."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from aikit import __version__, schemas
from aikit.compile_personas import (
    AGENT_PREFIX,
    agent_name,
    compile_persona,
    render_agents_block,
    splice_agents_block,
)
from aikit.core import GENERATED_MARK, Project, kit_root, write_if_changed
from aikit.index_builder import build_data, collect, stable_render
from aikit.merge import resolve


@dataclass
class BuildPlan:
    writes: dict[Path, str] = field(default_factory=dict)
    stale: list[Path] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    def pending(self) -> list[Path]:
        """Files whose content on disk differs from the plan."""
        out = [p for p, c in self.writes.items() if not p.is_file() or p.read_text(encoding="utf-8") != c]
        return out + self.stale


def agents_dir(project: Project) -> Path:
    return project.root / ".claude" / "agents"


def skills_dir(project: Project) -> Path:
    return project.root / ".claude" / "skills"


def plan(project: Project) -> BuildPlan:
    result = BuildPlan()
    personas, problems = resolve(project)
    result.problems += problems

    valid = [p for p in personas if not schemas.errors("persona", p.data)]
    expected: set[Path] = set()
    for persona in valid:
        if not persona.enabled:
            continue
        path = agents_dir(project) / f"{agent_name(persona.id)}.md"
        expected.add(path)
        result.writes[path] = compile_persona(persona, project)

    if agents_dir(project).is_dir():
        for path in sorted(agents_dir(project).glob(f"{AGENT_PREFIX}*.md")):
            if path not in expected and GENERATED_MARK in path.read_text(encoding="utf-8"):
                result.stale.append(path)

    if (project.ai / "manifest.json").is_file():  # skills only go into installed projects
        skills_src = kit_root() / "skills"
        for src in sorted(skills_src.rglob("*")):
            if src.is_file():
                rel = src.relative_to(skills_src)
                result.writes[skills_dir(project) / rel] = src.read_text(encoding="utf-8")

    agents_md = project.ai / "AGENTS.md"
    if agents_md.is_file():
        current = agents_md.read_text(encoding="utf-8")
        result.writes[agents_md] = splice_agents_block(current, render_agents_block(valid))

    data = build_data(project, valid, collect(project))
    result.problems += [f"index.yaml: {e}" for e in schemas.errors("index", data)]
    index = project.ai / "index.yaml"
    existing = index.read_text(encoding="utf-8") if index.is_file() else None
    result.writes[index] = stable_render(data, existing)
    return result


def apply(project: Project, build_plan: BuildPlan) -> list[str]:
    changed = [project.rel(p) for p, c in build_plan.writes.items() if write_if_changed(p, c)]
    for path in build_plan.stale:
        path.unlink()
        changed.append(f"{project.rel(path)} (removido)")

    manifest_path = project.ai / "manifest.json"
    if manifest_path.is_file():
        manifest = project.manifest()
        before = dict(manifest, files=sorted(manifest.get("files", [])))
        owned = (agents_dir(project), skills_dir(project))
        files = set(manifest.get("files", [])) - {project.rel(p) for p in build_plan.stale}
        files |= {project.rel(p) for p in build_plan.writes if any(d in p.parents for d in owned)}
        manifest["files"] = sorted(files)
        manifest["kit_version"] = __version__
        if manifest != before:
            project.save_manifest(manifest)
    return changed


def run(project: Project) -> tuple[list[str], list[str]]:
    build_plan = plan(project)
    return apply(project, build_plan), build_plan.problems
