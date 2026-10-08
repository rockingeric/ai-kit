"""Persona resolution: kit base, then overlays in order, then project override."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from aikit import schemas
from aikit.core import AikitError, Project, kit_root, load_yaml


def merge(base: dict, layer: dict) -> dict:
    """Lists add (deduplicated, order kept), dicts merge shallowly, scalars replace."""
    out = dict(base)
    for key, value in layer.items():
        current = out.get(key)
        if isinstance(current, list) and isinstance(value, list):
            out[key] = current + [v for v in value if v not in current]
        elif isinstance(current, dict) and isinstance(value, dict):
            out[key] = {**current, **value}
        else:
            out[key] = value
    return out


@dataclass
class Persona:
    data: dict
    sources: list[str]

    @property
    def id(self) -> str:
        return self.data["id"]

    @property
    def enabled(self) -> bool:
        return self.data.get("enabled", True)


def active_overlays(project: Project) -> list[str]:
    path = project.ai / "overlays.yaml"
    if not path.is_file():
        return []
    data = load_yaml(path) or []
    if not isinstance(data, list) or not all(isinstance(x, str) for x in data):
        raise AikitError(f"{path}: esperado uma lista de nomes, ex. [lgpd]")
    return data


def label(path: Path, project: Project) -> str:
    """Short path for messages and headers: `kit:personas/x.yaml` or `.ai/personas/x.yaml`."""
    in_project = project.ai.resolve() in path.resolve().parents
    order = ((project.root, ""), (kit_root(), "kit:")) if in_project else ((kit_root(), "kit:"), (project.root, ""))
    for base, prefix in order:
        try:
            return prefix + path.resolve().relative_to(base.resolve()).as_posix()
        except ValueError:
            continue
    return str(path)


def _layer(path: Path, persona_id: str, project: Project, problems: list[str]) -> dict:
    where = label(path, project)
    try:
        data = load_yaml(path) or {}
    except AikitError as exc:
        problems.append(f"{where}: {exc}".replace(str(path), where))
        return {}
    if not isinstance(data, dict):
        problems.append(f"{where}: persona precisa ser um mapa YAML")
        return {}
    if data.setdefault("id", persona_id) != persona_id:
        problems.append(f"{where}: id '{data['id']}' difere do nome do arquivo")
    for err in schemas.errors("persona-override", data):
        problems.append(f"{where}: {err}")
    return data


def resolve(project: Project) -> tuple[list[Persona], list[str]]:
    """Return merged personas (sorted by id) and the problems found on the way."""
    kit = kit_root()
    problems: list[str] = []
    layers: dict[str, list[tuple[Path, dict]]] = {}
    broken: set[str] = set()  # personas with an invalid layer: don't repeat its error on the merge

    def add(path: Path) -> None:
        before = len(problems)
        layers.setdefault(path.stem, []).append((path, _layer(path, path.stem, project, problems)))
        if len(problems) > before:
            broken.add(path.stem)

    for path in sorted((kit / "personas").glob("*.yaml")):
        add(path)
    for name in active_overlays(project):
        overlay = kit / "overlays" / name
        if not overlay.is_dir():
            problems.append(f".ai/overlays.yaml: overlay '{name}' não existe em {kit / 'overlays'}")
            continue
        for path in sorted((overlay / "personas").glob("*.yaml")):
            add(path)
    for path in sorted((project.ai / "personas").glob("*.yaml")):
        add(path)

    personas = []
    for persona_id, stack in sorted(layers.items()):
        merged: dict = {}
        for _, data in stack:
            merged = merge(merged, data)
        if persona_id not in broken:
            problems += [f"persona {persona_id}: {err}" for err in schemas.errors("persona", merged)]
        personas.append(Persona(merged, [label(p, project) for p, _ in stack]))
    return personas, problems
