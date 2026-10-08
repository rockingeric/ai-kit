"""Persona YAML -> Claude Code subagent markdown, plus the AGENTS.md persona block."""

from __future__ import annotations

import re

from aikit.core import GENERATED_MARK, Project, dump_yaml
from aikit.merge import Persona

AGENT_PREFIX = "aikit-"
BLOCK_START = "<!-- aikit:personas:start -->"
BLOCK_END = "<!-- aikit:personas:end -->"

READS_LABELS = {
    "project": "`project` (stack, comandos, convenções)",
    "decisions": "`decisions` (ADRs em `decisions_dir`; `accepted` é regra)",
    "personas": "`personas`",
    "wishes": "`wishes` (Genie)",
    "tutorial": "`docs.tutorial`",
    "how-to": "`docs.how-to` (runbooks)",
    "reference": "`docs.reference`",
    "explanation": "`docs.explanation`",
}


def agent_name(persona_id: str) -> str:
    return f"{AGENT_PREFIX}{persona_id}"


def _fill_paths(text: str, project: Project) -> str:
    def repl(m: re.Match) -> str:
        key = m.group(1)
        try:
            return project.rel(project.path(key)).rstrip("/")
        except KeyError:
            value = (project.config.get("paths") or {}).get(key)
            return value.rstrip("/") if value else m.group(0)

    return re.sub(r"\{paths\.(\w+)\}", repl, text)


def compile_persona(persona: Persona, project: Project) -> str:
    d = persona.data
    front = {
        "name": agent_name(d["id"]),
        "description": " ".join(d["description"].split()),
        "tools": ", ".join(d["tools"]),
        "model": d["model"],
    }
    sources = " + ".join(persona.sources)
    reads = ", ".join(READS_LABELS[r] for r in d["reads"])
    lines = [
        "---",
        dump_yaml(front).rstrip(),
        "---",
        f"<!-- {GENERATED_MARK}: não edite. Fonte: {sources}. "
        f"Mude .ai/personas/{d['id']}.yaml e rode `aikit build`. -->",
        "",
        f"Você é o **{d['id']}** deste projeto. Papel: {d['role']}.",
        "",
        "## Contexto",
        f"Comece por `.ai/index.yaml` e use só: {reads}. "
        "Abra apenas os arquivos que a tarefa pede; não abra docs de outros tipos nem varra o repo.",
    ]
    for title, key in (("Princípios", "principles"), ("Nunca", "never")):
        if d.get(key):
            lines += ["", f"## {title}", *(f"- {item}" for item in d[key])]
    if d.get("outputs"):
        lines += ["", "## Saídas"]
        lines += [f"- {k}: `{_fill_paths(v, project)}`" for k, v in d["outputs"].items()]
    if d.get("handoff"):
        lines += ["", "## Handoff", " ".join(d["handoff"].split())]
    return "\n".join(lines) + "\n"


def render_agents_block(personas: list[Persona]) -> str:
    lines = [
        BLOCK_START,
        "## Personas e gates",
        "O dev é a thread principal. Delegue pelo nome; com o Genie, cada gate chama a persona listada.",
    ]
    for p in personas:
        if not p.enabled:
            continue
        gates = ", ".join(p.data.get("gates") or []) or "sob demanda"
        lines.append(f"- `{agent_name(p.id)}`: {gates}")
    lines.append(BLOCK_END)
    return "\n".join(lines)


def splice_agents_block(agents_md: str, block: str) -> str:
    """Replace the generated block in AGENTS.md, or append it if missing."""
    pattern = re.compile(re.escape(BLOCK_START) + r".*?" + re.escape(BLOCK_END), re.S)
    if pattern.search(agents_md):
        return pattern.sub(lambda _: block, agents_md, count=1)
    return agents_md.rstrip("\n") + "\n\n" + block + "\n"
