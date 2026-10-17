# ai-kit

Instala em qualquer projeto um setup de personas, ADRs, runbooks e contexto enxuto para coding agents (Claude Code; Codex e Cursor via `AGENTS.md`).

- **Mecânica do kit é privada**: `.ai/`, subagents, skills e hook ficam fora do git do projeto, via `.git/info/exclude`. O `.gitignore` do time não é tocado.
- **Conhecimento é do time**: ADRs e runbooks vivem em `docs/`, versionados.
- **Contexto barato**: o agente lê `.ai/index.yaml` (~2k tokens no máximo) e abre só o que a tarefa pede. O `aikit lint` cobra os orçamentos.

O plano completo e as decisões estão em [`docs/plan.md`](docs/plan.md) e [`docs/decisions/`](docs/decisions/).

## Instalação (uma vez por máquina)

```sh
git clone <este repo> ~/ai-kit
uv tool install -e ~/ai-kit     # ou: pipx install -e ~/ai-kit
aikit backup --to ~/ai-kit-backups   # opcional agora; o doctor cobra depois
```

Atualizar o kit em todos os projetos: `git -C ~/ai-kit pull`, depois `aikit build` em cada projeto.

## Num projeto novo

```sh
cd meu-projeto
aikit init                 # ou: aikit init --overlay <nome>
```

Depois, no Claude Code: `/aikit-onboard`. Ele lê o repo e preenche `.ai/project.yaml` e `.ai/AGENTS.md`.

## Dia a dia

Antes de cada tarefa, o agente segue uma regra que fica no `AGENTS.md`: se cabe numa sessão e não restringe o futuro, só faz; se é uma escolha cara de desfazer, abre ADR; se atravessa várias sessões, abre um wish, que você aprova antes de o trabalho começar.

| Situação | O que fazer |
| --- | --- |
| Trabalho de várias sessões | O agente usa o skill `aikit-wish` (ou `aikit wish new "..."`) e para no `draft`; a sessão seguinte retoma pelo wish |
| Aprovar o escopo | Você revisa o wish e roda `aikit wish approve <slug>`: ele vira `approved` e nasce a branch `wish/<slug>` (com `git.worktrees: true`, num worktree `wt-<iniciais>-<slug>` ao lado do repo) |
| Antes de abrir o PR | `/aikit-ship`: testes, lint e as personas de revisão; devolve o veredito |
| Wish concluído | `aikit wish done <slug>` (sai do índice) |
| Começar trabalho com commit | Branch própria: `git switch -c <tipo>/<slug>` (o `aikit wish approve` já cria `wish/<slug>`). O Claude não consegue commitar na branch padrão |
| Decisão não trivial | O agente usa o skill `aikit-adr`; o ADR nasce `proposed` em `docs/decisions/` |
| Aceitar a decisão | `aikit adr accept 0007` (só você: o Claude é bloqueado de rodar) (grava `body_sha`, o corpo fica imutável) ou `aikit adr reject 0007` |
| Decisão substitui outra | `aikit adr new "..." --supersedes 0003` ou `aikit adr supersede 0003 0007` |
| Procedimento operacional | `aikit runbook new "Reverter deploy" --trigger "5xx após deploy"` |
| Runbook revisado | `aikit runbook verify reverter-deploy` |
| Docs desatualizados? | `/aikit-docs-sync` (usa `aikit lint --refs` e propõe correções) |
| Saúde da instalação | `aikit doctor` |
| Backup do `.ai/` | `aikit backup` |
| Remover o kit | `aikit uninstall` (o `docs/` fica) |

Branches: o kit impede o Claude de commitar na branch padrão (hook `PreToolUse`), e o `/aikit-ship` bloqueia o PR nela. A branch padrão vem de `origin/HEAD`, ou de `git.default_branch` no `.ai/project.yaml`; `git.enforce_branches: false` desliga a regra.

Worktrees (opt-in, ADR-0023): com `git.worktrees: true`, `aikit wish approve` abre `wish/<slug>` num worktree ao lado do repo, na pasta que o contém (repo em `~/code/hapvida/hap-content-agent` → `~/code/hapvida/wt-hca-<slug>`; `git.worktree_dir` troca a pasta), com o kit em symlink do checkout principal. Abra uma sessão nele com `cd <caminho> && claude`. O `aikit wish done` oferece remover o worktree se ele estiver limpo; a branch fica para o PR.

O índice se mantém sozinho. O hook `PostToolUse` roda `aikit build` quando o agente edita `.ai/` ou `docs/`, e todo comando `adr` e `runbook` também roda o build ao final.

### Sessões

Abra uma sessão nova a cada tarefa: o que importa fica no índice, nos wishes e nos ADRs, e não no histórico da conversa. Também abra uma sessão nova depois de mudar o `.ai/AGENTS.md`, porque ele só é lido quando a sessão começa. Overrides de persona, ADRs e wishes valem na sessão aberta.

## Personas

| Persona | Modelo | Gates | Lê do índice |
| --- | --- | --- | --- |
| `aikit-architect` | opus | wish, adr | project, decisions, explanation |
| `aikit-reviewer` | sonnet | ship | project, decisions, reference |
| `aikit-security` | opus | ship (se o diff for sensível) | project, decisions, how-to, reference |
| `aikit-qa` | sonnet | ship | project, wishes, how-to |
| `aikit-tech-writer` | haiku | sob demanda | todos os tipos de doc |

`wish` e `adr` indicam quem consultar ao planejar e ao decidir; `ship` indica quem o `/aikit-ship` chama.

O dev é a thread principal do Claude, não um subagent. Para ajustar uma persona num projeto, crie `.ai/personas/<id>.yaml` só com o que muda e rode `aikit build`. Listas somam e escalares substituem. `enabled: false` desliga a persona.

## O que fica onde

| Caminho | Git | O quê |
| --- | --- | --- |
| `docs/decisions/` | sim | ADRs (explanation) |
| `docs/runbooks/` | sim | Runbooks (how-to) |
| `docs/architecture/`, `reference/`, `guides/` | sim | Nascem com o primeiro doc (explanation, reference, tutorial) |
| `.ai/` | não | `project.yaml`, `AGENTS.md`, `index.yaml`, `wishes/`, overrides, notas, manifesto |
| `.claude/agents/aikit-*.md` | não | Subagents gerados (não edite) |
| `.claude/skills/aikit-*` | não | Skills copiados do kit |
| `CLAUDE.md` / `CLAUDE.local.md` | não | Importa `@.ai/AGENTS.md`. Se o time já versiona um `CLAUDE.md`, o import vai para `CLAUDE.local.md` |
| `AGENTS.md` | não | Symlink para `.ai/AGENTS.md` (Codex, Cursor) |

## Desenvolvimento

```sh
uv venv && uv pip install -e '.[dev]'
.venv/bin/pytest
```

Estrutura: `aikit/` (CLI), `personas/` (base), `overlays/`, `schemas/` (JSON Schema), `templates/`, `skills/`, `hooks/`, `docs/decisions/` (ADRs do próprio kit), `tests/`.
