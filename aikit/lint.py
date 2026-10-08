"""`aikit lint`: schemas, ADR integrity, Diátaxis types and context budgets."""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field

from aikit import build, schemas
from aikit.core import (
    AikitError,
    Project,
    body_sha,
    estimate_tokens,
    load_yaml,
    parse_doc,
    today,
)
from aikit.index_builder import Entry, adr_number, collect
from aikit.merge import resolve

AGENTS_MD_MAX_LINES = 60
PERSONA_MAX_LINES = 40
INDEX_MAX_TOKENS = 2000
ALWAYS_LOADED_MAX_TOKENS = 1500
MAX_PERSONAS = 5


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def error(self, where: str, msg: str) -> None:
        self.errors.append(f"{where}: {msg}")

    def warn(self, where: str, msg: str) -> None:
        self.warnings.append(f"{where}: {msg}")


def _frontmatter_description(text: str) -> str:
    m = re.search(r"^description:\s*(.+)$", text, re.M)
    return m.group(1) if m else ""


def _check_project(project: Project, report: Report) -> None:
    for err in schemas.errors("project", project.config):
        report.error(".ai/project.yaml", err)
    overlays = project.ai / "overlays.yaml"
    if overlays.is_file():
        try:
            load_yaml(overlays)
        except AikitError as exc:
            report.error(".ai/overlays.yaml", str(exc))


def _check_personas(project: Project, report: Report) -> None:
    personas, problems = resolve(project)
    for problem in problems:
        report.errors.append(problem)
    enabled = [p for p in personas if p.enabled]
    if len(enabled) > MAX_PERSONAS:
        report.warn("personas", f"{len(enabled)} ativas; o limite é {MAX_PERSONAS} (decisão 8)")


def _check_adrs(entries: list[Entry], report: Report) -> None:
    adrs = [e for e in entries if e.kind == "adr"]
    by_id: dict[str, Entry] = {}
    for entry in adrs:
        meta = entry.meta
        if not entry.doc.has_frontmatter:
            report.error(entry.rel, "ADR sem frontmatter")
            continue
        for err in schemas.errors("adr-frontmatter", meta):
            report.error(entry.rel, err)
        adr_id = meta.get("id", "")
        if adr_id and adr_number(entry.rel) != adr_number(adr_id):
            report.error(entry.rel, f"id {adr_id} não bate com o nome do arquivo")
        if adr_id in by_id:
            report.error(entry.rel, f"id {adr_id} duplicado ({by_id[adr_id].rel})")
        by_id[adr_id] = entry

        sha = meta.get("body_sha")
        if meta.get("status") == "accepted" and sha is None:
            report.error(entry.rel, "accepted sem body_sha; rode `aikit adr accept`")
        if sha and sha != body_sha(entry.doc.body):
            report.error(
                entry.rel,
                "corpo mudou depois do aceite (body_sha não bate). Reverta ou crie um ADR que o substitua",
            )

    for adr_id, entry in by_id.items():
        meta = entry.meta
        target = meta.get("superseded_by")
        if meta.get("status") == "superseded" and not target:
            report.error(entry.rel, "superseded sem superseded_by")
        if target:
            other = by_id.get(target)
            if not other:
                report.error(entry.rel, f"superseded_by aponta para {target}, que não existe")
            elif other.meta.get("supersedes") != adr_id:
                report.error(entry.rel, f"{target} não declara supersedes: {adr_id}")
        source = meta.get("supersedes")
        if source:
            other = by_id.get(source)
            if not other:
                report.error(entry.rel, f"supersedes aponta para {source}, que não existe")
            elif other.meta.get("superseded_by") != adr_id:
                report.error(entry.rel, f"{source} não está marcado como superseded_by {adr_id}")


def _check_docs(project: Project, entries: list[Entry], report: Report) -> None:
    for entry in entries:
        meta = entry.meta
        if entry.kind == "runbook":
            if not entry.doc.has_frontmatter:
                report.error(entry.rel, "runbook sem frontmatter")
                continue
            for err in schemas.errors("runbook-frontmatter", meta):
                report.error(entry.rel, err)
            verified = meta.get("last_verified")
            if isinstance(verified, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", verified):
                age = (today() - dt.date.fromisoformat(verified)).days
                if age > project.max_age_days:
                    report.warn(
                        entry.rel,
                        f"last_verified há {age} dias (limite {project.max_age_days}); "
                        "revise e rode `aikit runbook verify`",
                    )
        elif entry.kind == "wish":
            for err in schemas.errors("wish-frontmatter", meta):
                report.error(entry.rel, err)
            for adr in meta.get("adrs") or []:
                if not any(e.kind == "adr" and e.meta.get("id") == adr for e in entries):
                    report.error(entry.rel, f"cita {adr}, que não existe")
            continue
        elif entry.kind in ("doc", "note"):
            for err in schemas.errors("doc-frontmatter", meta):
                report.error(entry.rel, err)
        if entry.kind == "note" and not meta.get("type"):
            report.error(entry.rel, "nota em .ai/docs sem `type:` Diátaxis no frontmatter")
        declared = meta.get("type")
        if declared and entry.folder_type and declared != entry.folder_type:
            report.error(entry.rel, f"type: {declared} contradiz a pasta ({entry.folder_type})")


def _check_budgets(project: Project, report: Report) -> None:
    build_plan = build.plan(project)
    always_loaded = 0
    agents_md = project.ai / "AGENTS.md"
    if agents_md.is_file():
        text = build_plan.writes.get(agents_md) or agents_md.read_text(encoding="utf-8")
        lines = text.count("\n")
        if lines > AGENTS_MD_MAX_LINES:
            report.warn(".ai/AGENTS.md", f"{lines} linhas; orçamento é {AGENTS_MD_MAX_LINES}")
        always_loaded += estimate_tokens(text)

    for path, content in build_plan.writes.items():
        if path.parent == build.agents_dir(project):
            lines = content.count("\n")
            if lines > PERSONA_MAX_LINES:
                report.warn(project.rel(path), f"{lines} linhas compiladas; orçamento é {PERSONA_MAX_LINES}")
            always_loaded += estimate_tokens(_frontmatter_description(content))

    skills = project.root / ".claude" / "skills"
    for skill in sorted(skills.glob("aikit-*/SKILL.md")) if skills.is_dir() else []:
        text = skill.read_text(encoding="utf-8")
        if not re.search(r"^disable-model-invocation:\s*true\s*$", text, re.M):
            always_loaded += estimate_tokens(_frontmatter_description(text))

    if always_loaded > ALWAYS_LOADED_MAX_TOKENS:
        report.warn(
            "contexto fixo",
            f"~{always_loaded} tokens (AGENTS.md + descriptions); orçamento é {ALWAYS_LOADED_MAX_TOKENS}",
        )

    index = build_plan.writes[project.ai / "index.yaml"]
    tokens = estimate_tokens(index)
    if tokens > INDEX_MAX_TOKENS:
        report.warn(".ai/index.yaml", f"~{tokens} tokens; orçamento é {INDEX_MAX_TOKENS}")


_REF_RE = re.compile(r"`([^`\s]+)`")
_EXTS = "md|py|pyi|ts|tsx|js|jsx|mjs|json|ya?ml|toml|ini|cfg|env|sh|go|rs|rb|java|kt|sql|txt|lock|css|html|tf"
_PATHLIKE = re.compile(rf"^[\w.@-][\w./@-]*(/[\w.@-]*|\.(?:{_EXTS}))$")


def check_refs(project: Project, entries: list[Entry], report: Report) -> None:
    """Paths cited in backticks that no longer exist (mechanical half of docs-sync)."""
    for entry in entries:
        if entry.kind == "adr" and entry.meta.get("status") != "proposed":
            continue  # accepted bodies are immutable history; only proposals can still be fixed
        in_fence = False
        for line in entry.doc.body.splitlines():
            if line.lstrip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            for ref in _REF_RE.findall(line):
                ref = ref.rstrip(".,;:")
                if not _PATHLIKE.match(ref) or ref.startswith(("http", "~", "-")) or "{" in ref:
                    continue
                if not (project.root / ref).exists():
                    report.warn(entry.rel, f"cita `{ref}`, que não existe")


def run(project: Project, refs: bool = False) -> Report:
    report = Report()
    _check_project(project, report)
    _check_personas(project, report)
    entries = collect(project)
    _check_adrs(entries, report)
    _check_docs(project, entries, report)
    _check_budgets(project, report)
    if any((project.ai / "plans").glob("*.md")):
        report.warn(
            ".ai/plans",
            "planos da 0.3 não entram mais no índice: mova para .ai/wishes, troque id PL- por WISH- "
            "e status active por approved",
        )
    if refs:
        check_refs(project, entries, report)
    return report
