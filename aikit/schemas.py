"""JSON Schema loading and validation, with compact one-line error messages."""

from __future__ import annotations

import copy
import json
from functools import cache
from typing import Any

from jsonschema import Draft202012Validator

from aikit.core import kit_root


@cache
def _schema(name: str) -> dict:
    if name == "persona-override":
        schema = copy.deepcopy(_schema("persona"))
        schema.pop("required")
        schema["title"] = "persona-override"
        return schema
    path = kit_root() / "schemas" / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def errors(name: str, data: Any) -> list[str]:
    validator = Draft202012Validator(_schema(name))
    out = []
    for err in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path)):
        where = ".".join(str(p) for p in err.absolute_path) or "(raiz)"
        out.append(f"{where}: {err.message}")
    return out
