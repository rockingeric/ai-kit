"""ADR, runbook and wish lifecycle: new, supersede, accept, reject, verify, approve, done."""

from __future__ import annotations

import re
from pathlib import Path

from aikit.core import (
    AikitError,
    Project,
    body_sha,
    kit_root,
    parse_doc,
    scalar,
    set_fields,
    slugify,
    today,
)
from aikit.index_builder import SUMMARY_MAX, adr_number


def _render(template: str, values: dict) -> str:
    text = (kit_root() / "templates" / template).read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", scalar(value))
    return text


def _short(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= SUMMARY_MAX else text[: SUMMARY_MAX - 1] + "…"


def adr_id(n: int) -> str:
    return f"ADR-{n:04d}"


def parse_ref(ref: str) -> int:
    digits = ref.upper().removeprefix("ADR-")
    if not digits.isdigit():
        raise AikitError(f"referência de ADR inválida: {ref} (use 3, 0003 ou ADR-0003)")
    return int(digits)


def find_adr(project: Project, ref: str | int) -> Path:
    n = ref if isinstance(ref, int) else parse_ref(ref)
    matches = sorted(project.path("adr").glob(f"ADR-{n:04d}*.md"))
    if not matches:
        raise AikitError(f"{adr_id(n)} não encontrado em {project.rel(project.path('adr'))}")
    if len(matches) > 1:
        raise AikitError(f"{adr_id(n)} ambíguo: {', '.join(p.name for p in matches)}")
    return matches[0]


def new_adr(
    project: Project,
    title: str,
    tags: list[str] | None = None,
    summary: str | None = None,
    supersedes: str | None = None,
) -> Path:
    folder = project.path("adr")
    folder.mkdir(parents=True, exist_ok=True)
    numbers = [adr_number(p.name) for p in folder.glob("ADR-*.md")]
    n = max(numbers, default=0) + 1
    old = find_adr(project, supersedes) if supersedes else None
    path = folder / f"{adr_id(n)}-{slugify(title)}.md"
    path.write_text(
        _render(
            "adr.md",
            {
                "id": adr_id(n),
                "title": title,
                "date": today().isoformat(),
                "supersedes": None,
                "tags": tags or [],
                "summary": _short(summary or title),
            },
        ),
        encoding="utf-8",
    )
    if old:
        supersede(project, adr_id(adr_number(old.name)), adr_id(n))
    return path


def supersede(project: Project, old_ref: str, new_ref: str) -> tuple[Path, Path]:
    old_path, new_path = find_adr(project, old_ref), find_adr(project, new_ref)
    if old_path == new_path:
        raise AikitError("um ADR não pode substituir a si mesmo")
    old, new = parse_doc(old_path).meta or {}, parse_doc(new_path).meta or {}
    if old.get("superseded_by") not in (None, new["id"]):
        raise AikitError(f"{old['id']} já foi substituído por {old['superseded_by']}")
    if old.get("status") == "rejected":
        raise AikitError(f"{old['id']} está rejected; não há o que substituir")
    set_fields(old_path, {"status": "superseded", "superseded_by": new["id"]})
    set_fields(new_path, {"supersedes": old["id"]})
    return old_path, new_path


def accept(project: Project, ref: str) -> tuple[Path, bool]:
    """Return (path, changed). Freezes the body by recording its sha."""
    path = find_adr(project, ref)
    doc = parse_doc(path)
    meta = doc.meta or {}
    status, sha = meta.get("status"), body_sha(doc.body)
    if status in ("superseded", "rejected"):
        raise AikitError(f"{meta.get('id')} está {status}; não pode ser aceito")
    if status == "accepted":
        if meta.get("body_sha") != sha:
            raise AikitError(
                f"{meta.get('id')} já está accepted, mas o corpo mudou desde o aceite. "
                "Corpo de ADR aceito é imutável: reverta a edição ou crie um ADR novo que o substitua."
            )
        return path, False
    set_fields(path, {"status": "accepted", "body_sha": sha})
    return path, True


def reject(project: Project, ref: str) -> Path:
    path = find_adr(project, ref)
    meta = parse_doc(path).meta or {}
    if meta.get("status") != "proposed":
        raise AikitError(f"{meta.get('id')} está {meta.get('status')}; só proposed pode ser rejeitado")
    set_fields(path, {"status": "rejected"})
    return path


def new_runbook(
    project: Project,
    title: str,
    trigger: str | None = None,
    tags: list[str] | None = None,
    summary: str | None = None,
) -> Path:
    slug = slugify(title)
    folder = project.path("runbooks")
    path = folder / f"{slug}.md"
    if path.exists():
        raise AikitError(f"{project.rel(path)} já existe")
    folder.mkdir(parents=True, exist_ok=True)
    path.write_text(
        _render(
            "runbook.md",
            {
                "id": f"RB-{slug}",
                "title": title,
                "trigger": trigger or "",
                "date": today().isoformat(),
                "tags": tags or [],
                "summary": _short(summary or title),
            },
        ),
        encoding="utf-8",
    )
    return path


def verify_runbook(project: Project, ref: str) -> Path:
    slug = ref.removeprefix("RB-").removesuffix(".md")
    path = project.path("runbooks") / f"{slug}.md"
    if not path.is_file():
        raise AikitError(f"runbook {slug} não encontrado em {project.rel(project.path('runbooks'))}")
    set_fields(path, {"last_verified": today().isoformat()})
    return path


def _wish_path(project: Project, ref: str) -> Path:
    slug = ref.removeprefix("WISH-").removeprefix("wish/").removesuffix(".md")
    path = project.ai / "wishes" / f"{slug}.md"
    if not path.is_file():
        raise AikitError(f"wish {slug} não encontrado em .ai/wishes")
    return path


def _criteria(body: str) -> tuple[list[str], list[str]]:
    """(open, done) acceptance criteria with text; empty template lines don't count."""
    section = re.search(r"^## Critérios de aceite\n(.*?)(?=^## |\Z)", body, re.S | re.M)
    text = section.group(1) if section else ""
    return (
        re.findall(r"^- \[ \] *(\S.*)$", text, re.M),
        re.findall(r"^- \[[xX]\] *(\S.*)$", text, re.M),
    )


def new_wish(project: Project, title: str, summary: str | None = None) -> Path:
    """Create a draft wish. No branch yet: work starts only after the human approves it."""
    slug = slugify(title)
    path = project.ai / "wishes" / f"{slug}.md"
    if path.exists():
        raise AikitError(f"{project.rel(path)} já existe")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        _render(
            "wish.md",
            {"id": f"WISH-{slug}", "title": title, "date": today().isoformat(), "summary": _short(summary or title)},
        ),
        encoding="utf-8",
    )
    return path


def approve_wish(project: Project, ref: str) -> tuple[Path, str | None]:
    """Human-only: draft -> approved, then open `wish/<slug>` (switch or worktree). Returns (path, branch note)."""
    path = _wish_path(project, ref)
    doc = parse_doc(path)
    status = (doc.meta or {}).get("status")
    if status != "draft":
        raise AikitError(f"{path.stem} está {status}; só draft pode ser aprovado")
    open_items, done_items = _criteria(doc.body)
    if not open_items and not done_items:
        raise AikitError(f"{path.stem} não tem critérios de aceite preenchidos; não há o que aprovar")
    if project.worktrees:
        from aikit import worktree

        note = worktree.ensure(project, path.stem)
    else:
        note = project.ensure_branch(f"wish/{path.stem}")
    set_fields(path, {"status": "approved", "approved": today().isoformat()})
    return path, note


def finish_wish(project: Project, ref: str) -> tuple[Path, list[str]]:
    """approved -> done; returns the acceptance criteria still unchecked."""
    path = _wish_path(project, ref)
    doc = parse_doc(path)
    status = (doc.meta or {}).get("status")
    if status != "approved":
        raise AikitError(f"{path.stem} está {status}; só wish approved pode ser concluído")
    set_fields(path, {"status": "done"})
    return path, _criteria(doc.body)[0]
