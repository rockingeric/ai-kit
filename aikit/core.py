"""Shared plumbing: kit/project paths, YAML and frontmatter I/O, idempotent writes."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

AI_DIR = ".ai"
DEFAULT_PATHS = {
    "adr": "docs/decisions/",
    "runbooks": "docs/runbooks/",
    "docs": "docs/",
}
# Diátaxis type implied by each folder under paths.docs (decision 12).
FOLDER_TYPES = {
    "architecture": "explanation",
    "reference": "reference",
    "guides": "tutorial",
}
DIATAXIS = ("tutorial", "how-to", "reference", "explanation")
GENERATED_MARK = "aikit:generated"


class AikitError(Exception):
    """User-facing error: printed without a traceback."""


def kit_root() -> Path:
    env = os.environ.get("AIKIT_HOME")
    root = Path(env).expanduser() if env else Path(__file__).resolve().parent.parent
    if not (root / "personas").is_dir():
        raise AikitError(
            f"kit não encontrado em {root} (sem personas/). "
            "Instale com `uv tool install -e ~/ai-kit` ou defina AIKIT_HOME."
        )
    return root


def today() -> dt.date:
    override = os.environ.get("AIKIT_TODAY")
    return dt.date.fromisoformat(override) if override else dt.date.today()


# --- YAML -------------------------------------------------------------------


def _plain(value: Any) -> Any:
    """YAML loads dates as objects; schemas and comparisons want ISO strings."""
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_plain(v) for v in value]
    return value


def load_yaml_text(text: str, source: str = "<yaml>") -> Any:
    try:
        return _plain(yaml.safe_load(text))
    except yaml.YAMLError as exc:
        raise AikitError(f"{source}: YAML inválido ({exc.__class__.__name__}: {exc})") from exc


def load_yaml(path: Path) -> Any:
    return load_yaml_text(path.read_text(encoding="utf-8"), str(path))


def dump_yaml(data: Any) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=1000)


def _dates(value: Any) -> Any:
    if isinstance(value, str) and _ISO_DATE.match(value):
        return dt.date.fromisoformat(value)
    if isinstance(value, dict):
        return {k: _dates(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_dates(v) for v in value]
    return value


def flow(data: Any) -> str:
    """One-line YAML for an index entry: `{id: X, tags: [a, b]}`, dates unquoted."""
    return yaml.safe_dump(
        _dates(data), default_flow_style=True, sort_keys=False, allow_unicode=True, width=10_000
    ).strip()


_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, str) and _ISO_DATE.match(value):
        return value  # unquoted on purpose: load_yaml turns it back into the same string
    out = yaml.safe_dump(value, default_flow_style=True, allow_unicode=True, width=10_000)
    return out.replace("\n...\n", "").strip()


# --- Frontmatter ------------------------------------------------------------

_FM_RE = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.S)


@dataclass
class Doc:
    path: Path
    meta: dict | None
    fm_text: str
    body: str

    @property
    def has_frontmatter(self) -> bool:
        return self.meta is not None


def parse_doc(path: Path) -> Doc:
    text = path.read_text(encoding="utf-8")
    m = _FM_RE.match(text)
    if not m:
        return Doc(path, None, "", text)
    meta = load_yaml_text(m.group(1), str(path)) or {}
    if not isinstance(meta, dict):
        raise AikitError(f"{path}: frontmatter precisa ser um mapa YAML")
    return Doc(path, meta, m.group(1), text[m.end():])


def body_sha(body: str) -> str:
    normalized = body.replace("\r\n", "\n").strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def set_fields(path: Path, updates: dict[str, Any]) -> None:
    """Rewrite single frontmatter keys in place; the body stays byte-identical."""
    text = path.read_text(encoding="utf-8")
    m = _FM_RE.match(text)
    if not m:
        raise AikitError(f"{path}: sem frontmatter")
    fm = m.group(1)
    for key, value in updates.items():
        line = f"{key}: {scalar(value)}"
        pattern = re.compile(rf"^{re.escape(key)}:.*$", re.M)
        fm = pattern.sub(lambda _: line, fm, count=1) if pattern.search(fm) else f"{fm}\n{line}"
    path.write_text(f"---\n{fm}\n---\n{text[m.end():]}", encoding="utf-8")


def first_heading(body: str) -> str | None:
    for line in body.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


# --- Files ------------------------------------------------------------------


def write_if_changed(path: Path, content: str) -> bool:
    if path.is_file() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def slugify(title: str) -> str:
    import unicodedata

    ascii_title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_title.lower()).strip("-")
    return slug[:40].rstrip("-") or "sem-titulo"


def estimate_tokens(text: str) -> int:
    return len(text) // 4


# --- Git --------------------------------------------------------------------


def git(root: Path, *args: str) -> str | None:
    try:
        out = subprocess.run(
            ["git", *args], cwd=root, capture_output=True, text=True, check=True, timeout=10
        )
    # A hung git (odd mount, fifo) must not hang hooks; callers treat None as unknown.
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return None
    return out.stdout.strip()


def git_toplevel(start: Path) -> Path | None:
    out = git(start, "rev-parse", "--show-toplevel")
    return Path(out) if out else None


def is_tracked(root: Path, rel: str) -> bool:
    return bool(git(root, "ls-files", "--", rel))


def current_branch(root: Path) -> str | None:
    """Branch name, also on an unborn branch; None when detached or outside git."""
    return git(root, "symbolic-ref", "--quiet", "--short", "HEAD") or None


# --- Project ----------------------------------------------------------------


@dataclass
class Project:
    root: Path
    config: dict = field(default_factory=dict)

    @property
    def ai(self) -> Path:
        return self.root / AI_DIR

    def path(self, key: str) -> Path:
        rel = (self.config.get("paths") or {}).get(key) or DEFAULT_PATHS[key]
        return self.root / rel

    def rel(self, p: Path) -> str:
        return p.relative_to(self.root).as_posix()

    @property
    def name(self) -> str:
        return self.config.get("name") or self.root.name

    @property
    def max_age_days(self) -> int:
        return int(self.config.get("docs_max_age_days", 90))

    @property
    def enforce_branches(self) -> bool:
        return bool((self.config.get("git") or {}).get("enforce_branches", True))

    @property
    def worktrees(self) -> bool:
        return bool((self.config.get("git") or {}).get("worktrees", False))

    def default_branch(self) -> str:
        configured = (self.config.get("git") or {}).get("default_branch")
        if configured:
            return configured
        remote = git(self.root, "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD")
        if remote:
            return remote.split("/", 1)[1]
        return git(self.root, "config", "init.defaultBranch") or "main"

    def ensure_branch(self, name: str) -> str | None:
        """Switch to `name`, creating it from HEAD if needed. Returns a note, or None if nothing changed."""
        if not self.enforce_branches or git(self.root, "rev-parse", "--git-dir") is None:
            return None
        if current_branch(self.root) == name:
            return None
        exists = git(self.root, "rev-parse", "--verify", "--quiet", f"refs/heads/{name}") is not None
        args = ("switch", name) if exists else ("switch", "-c", name)
        try:
            subprocess.run(["git", *args], cwd=self.root, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as exc:
            raise AikitError(f"não consegui trocar para a branch {name}: {exc.stderr.strip()}") from exc
        return f"branch {name} {'(já existia)' if exists else 'criada'}; você está nela agora"

    def manifest(self) -> dict:
        path = self.ai / "manifest.json"
        if not path.is_file():
            return {"files": [], "edits": []}
        return json.loads(path.read_text(encoding="utf-8"))

    def save_manifest(self, data: dict) -> None:
        data["files"] = sorted(set(data.get("files", [])))
        write_if_changed(
            self.ai / "manifest.json", json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        )


def find_root(start: Path | None = None) -> Path:
    start = (start or Path.cwd()).resolve()
    for candidate in (start, *start.parents):
        if (candidate / AI_DIR / "project.yaml").is_file():
            return candidate
    return git_toplevel(start) or start


def load_project(start: Path | None = None, *, required: bool = True) -> Project:
    root = find_root(start)
    cfg_path = root / AI_DIR / "project.yaml"
    if not cfg_path.is_file():
        if required:
            raise AikitError(f"{root}: sem .ai/project.yaml. Rode `aikit init` primeiro.")
        return Project(root)
    return Project(root, load_yaml(cfg_path) or {})
