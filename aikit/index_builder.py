"""Collect ADRs, runbooks, docs and Genie wishes; render .ai/index.yaml."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from aikit.core import (
    DIATAXIS,
    FOLDER_TYPES,
    AikitError,
    Doc,
    Project,
    first_heading,
    flow,
    parse_doc,
    today,
)
from aikit.merge import Persona

INDEX_HEADER = "# Gerado por `aikit build`; não edite. Leia primeiro e abra só o que a tarefa pede.\n"
COLLAPSED_STATUSES = {"superseded", "rejected"}
SUMMARY_MAX = 80


@dataclass
class Entry:
    doc: Doc
    rel: str
    kind: str  # adr | runbook | doc | note
    folder_type: str | None  # type implied by the folder; None for .ai/docs

    @property
    def meta(self) -> dict:
        return self.doc.meta or {}

    @property
    def doc_type(self) -> str | None:
        return self.meta.get("type") or self.folder_type


def _md_files(folder: Path, pattern: str = "*.md") -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.rglob(pattern) if p.is_file() and p.name.lower() != "readme.md")


def adr_number(path_or_id: str) -> int:
    m = re.search(r"ADR-(\d{4})", str(path_or_id))
    if not m:
        raise AikitError(f"não é um ADR: {path_or_id}")
    return int(m.group(1))


def collect(project: Project) -> list[Entry]:
    entries: list[Entry] = []
    seen: set[Path] = set()

    def add(path: Path, kind: str, folder_type: str | None) -> None:
        path = path.resolve()
        if path in seen:
            return
        seen.add(path)
        entries.append(Entry(parse_doc(path), project.rel(path), kind, folder_type))

    for path in _md_files(project.path("adr"), "ADR-*.md"):
        add(path, "adr", "explanation")
    for path in _md_files(project.path("runbooks")):
        add(path, "runbook", "how-to")
    docs_root = project.path("docs")
    for folder, doc_type in FOLDER_TYPES.items():
        for path in _md_files(docs_root / folder):
            add(path, "doc", doc_type)
    for path in _md_files(project.ai / "docs"):
        add(path, "note", None)
    return entries


def collect_wishes(project: Project) -> list[dict]:
    root = project.root / ".genie" / "wishes"
    if not root.is_dir():
        return []
    wishes = []
    for item in sorted(root.iterdir()):
        if item.is_dir():
            files = sorted(item.glob("*wish*.md")) or sorted(item.glob("*.md"))
            slug, source = item.name, files[0] if files else None
        elif item.suffix == ".md":
            slug, source = re.sub(r"-wish$", "", item.stem), item
        else:
            continue
        status = _wish_status(source) if source else None
        wishes.append({"slug": slug, "status": status} if status else {"slug": slug})
    return wishes


def _wish_status(path: Path) -> str | None:
    doc = parse_doc(path)
    if doc.meta and doc.meta.get("status"):
        return str(doc.meta["status"])
    for line in doc.body.splitlines()[:40]:
        m = re.search(r"status\W{0,4}:\W*\s*([A-Za-z][A-Za-z_-]*)", line, re.I)
        if m:
            return m.group(1)
    return None


def _summary(entry: Entry) -> str | None:
    text = entry.meta.get("summary") or entry.meta.get("title") or first_heading(entry.doc.body)
    if not text:
        return None
    text = " ".join(str(text).split())
    return text if len(text) <= SUMMARY_MAX else text[: SUMMARY_MAX - 1] + "…"


def _decision_item(entry: Entry) -> dict:
    meta = entry.meta
    status = meta.get("status", "?")
    item = {"id": meta.get("id") or Path(entry.rel).stem[:8], "status": status}
    if status in COLLAPSED_STATUSES:
        return item
    if meta.get("tags"):
        item["tags"] = meta["tags"]
    if summary := _summary(entry):
        item["summary"] = summary
    return item


def _doc_item(entry: Entry) -> dict:
    meta = entry.meta
    item: dict = {}
    if meta.get("id"):
        item["id"] = meta["id"]
    item["path"] = entry.rel
    if meta.get("tags"):
        item["tags"] = meta["tags"]
    if meta.get("last_verified"):
        item["last_verified"] = meta["last_verified"]
    if summary := _summary(entry):
        item["summary"] = summary
    return item


def build_data(project: Project, personas: list[Persona], entries: list[Entry]) -> dict:
    adrs = sorted((e for e in entries if e.kind == "adr"), key=lambda e: e.rel, reverse=True)
    docs: dict[str, list[dict]] = {}
    for entry in entries:
        if entry.kind == "adr":
            continue
        doc_type = entry.doc_type
        if doc_type in DIATAXIS:  # untyped notes are reported by lint, not indexed
            docs.setdefault(doc_type, []).append(_doc_item(entry))
    data: dict = {
        "generated": today().isoformat(),
        "project": ".ai/project.yaml",
        "personas": [p.id for p in personas if p.enabled],
    }
    if adrs:
        data["decisions_dir"] = project.rel(project.path("adr"))
        data["decisions"] = [_decision_item(e) for e in adrs]
    if docs:
        data["docs"] = {t: docs[t] for t in ("explanation", "how-to", "reference", "tutorial") if t in docs}
    if wishes := collect_wishes(project):
        data["wishes"] = wishes
    return data


def render(data: dict) -> str:
    lines = [INDEX_HEADER.rstrip("\n")]
    lines.append(f"generated: {data['generated']}")
    lines.append(f"project: {data['project']}")
    lines.append(f"personas: {flow(data['personas'])}")
    if "decisions" in data:
        lines.append(f"decisions_dir: {data['decisions_dir']}  # arquivo: <id>-*.md")
        lines.append("decisions:")
        lines += [f"  - {flow(d)}" for d in data["decisions"]]
    if "docs" in data:
        lines.append("docs:")
        for doc_type, items in data["docs"].items():
            lines.append(f"  {doc_type}:")
            lines += [f"    - {flow(i)}" for i in items]
    if "wishes" in data:
        lines.append("wishes:")
        lines += [f"  - {flow(w)}" for w in data["wishes"]]
    return "\n".join(lines) + "\n"


_GENERATED_RE = re.compile(r"^generated: .*$", re.M)


def stable_render(data: dict, existing: str | None) -> str:
    """Keep the previous `generated` date when nothing else changed."""
    content = render(data)
    if existing and _GENERATED_RE.sub("", existing) == _GENERATED_RE.sub("", content):
        return existing
    return content
