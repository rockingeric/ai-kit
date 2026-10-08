"""Persona YAML -> Claude Code subagent markdown, plus the kit-owned block of AGENTS.md."""

from __future__ import annotations

import re

from aikit.core import GENERATED_MARK, Project, dump_yaml
from aikit.merge import Persona

AGENT_PREFIX = "aikit-"
BLOCK_START = "<!-- aikit:start (gerado por `aikit build`; não edite) -->"
BLOCK_END = "<!-- aikit:end -->"
_BLOCK_RE = re.compile(r"<!-- aikit:(?:personas:)?start.*?-->.*?<!-- aikit:(?:personas:)?end -->", re.S)

# Kit rules live in the generated block so `aikit build` updates every project.
WORKFLOW_RULES = """\
## Como trabalhar aqui (ai-kit)
- Leia `.ai/index.yaml` antes de explorar o repo e abra só o que a tarefa pede.
- Antes de começar uma tarefa, decida o artefato:
  - cabe numa sessão e não restringe o futuro → só faça;
  - escolha cara de desfazer, ou que um agente contrariaria sem saber → ADR (skill `aikit-adr`);
  - trabalho de várias sessões → plano (skill `aikit-plan`); decisões estruturais dentro dele → ADR;
  - na dúvida, pergunte ao humano em uma linha em vez de criar artefato.
- Plano `active` no índice é trabalho em andamento: retome por ele e atualize "Próxima sessão" antes de parar.
- ADR `accepted` é regra; para mudar, ADR novo com `--supersedes`. Só o humano aceita.
- Procedimento operacional → `aikit runbook new "título"`.
- `.claude/agents/aikit-*.md` é gerado: mude `.ai/personas/<id>.yaml` e rode `aikit build`."""

# The pre-0.2 template shipped these rules as a hand-owned section; drop it if untouched.
LEGACY_SECTION = """\
## Como trabalhar aqui
- Antes de explorar o repo, leia `.ai/index.yaml` e abra só o que a tarefa pede.
- ADR `accepted` é regra do projeto: não contrarie sem um ADR novo que o substitua.
- Decisão não trivial → skill `aikit-adr` (nasce `proposed`; só o humano aceita).
- Procedimento operacional novo → `aikit runbook new "título"`.
- `.claude/agents/aikit-*.md` é gerado: mude `.ai/personas/<id>.yaml` e rode `aikit build`.
"""

READS_LABELS = {
    "project": "`project` (stack, comandos, convenções)",
    "decisions": "`decisions` (ADRs em `decisions_dir`; `accepted` é regra)",
    "personas": "`personas`",
    "plans": "`plans` (critérios de aceite do plano ativo)",
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
        WORKFLOW_RULES,
        "",
        "## Personas",
        "O dev é a thread principal; delegue pelo nome. Gates: `plan` e `adr` = consultar ao planejar "
        "e decidir; `ship` = chamada pelo `/aikit-ship` antes do PR.",
    ]
    for p in personas:
        if not p.enabled:
            continue
        gates = ", ".join(p.data.get("gates") or []) or "sob demanda"
        lines.append(f"- `{agent_name(p.id)}`: {gates}")
    lines.append(BLOCK_END)
    return "\n".join(lines)


def splice_agents_block(agents_md: str, block: str) -> str:
    """Replace the generated block in AGENTS.md (current or legacy markers), or append it."""
    agents_md = agents_md.replace(LEGACY_SECTION + "\n", "").replace(LEGACY_SECTION, "")
    if _BLOCK_RE.search(agents_md):
        return _BLOCK_RE.sub(lambda _: block, agents_md, count=1)
    return agents_md.rstrip("\n") + "\n\n" + block + "\n"
