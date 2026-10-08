---
id: ADR-0019
title: Uma branch por trabalho; commit do agente na branch padrão é bloqueado
status: accepted
date: 2026-10-08
supersedes: null
superseded_by: null
body_sha: d4be1b6583a93f1134d02a47dd26233c1b23153c29f0a0bcaa5b57201ddfd643
tags: [git, branches, hooks]
summary: plan new cria plan/<slug>; hook PreToolUse barra commit na branch padrão
---
## Contexto

Sem o Genie, nada no kit separava o trabalho em branches: o agente podia commitar direto na branch padrão. O humano quer que isso seja imposto, não só recomendado.

## Opções

- **Só instrução no AGENTS.md**: custo zero, mas depende de o agente lembrar.
- **Git hook `pre-commit` em `.git/hooks`**: pega também commits humanos, mas conflita com husky, pre-commit e similares que o time já usa.
- **Worktree por tarefa**: isolamento máximo, mas pesa no fluxo de quem trabalha num checkout só.
- **Três camadas leves**: `aikit plan new` cria e troca para `plan/<slug>`; hook `PreToolUse` do Claude Code barra `git commit` na branch padrão (exit 2, mensagem volta ao agente); `/aikit-ship` devolve BLOQUEADO na branch padrão.

## Decisão

Três camadas leves. A branch padrão vem de `git.default_branch` no `project.yaml`, depois de `origin/HEAD`, depois de `init.defaultBranch`, e por fim `main`. `git.enforce_branches: false` desliga por projeto. O `aikit build` instala os hooks do kit, então atualizar um projeto não exige rodar `init` de novo.

## Consequências

- Mais fácil: todo trabalho do agente chega como branch revisável; planos têm branch com nome previsível.
- Mais difícil: o hook roda em toda chamada de Bash (só lê o projeto quando há `git commit` em posição de comando; menções em texto, echo ou heredoc não contam). Formas exóticas, como um alias de git ou um script que commita, passam sem bloqueio.
- Commits feitos pelo humano no terminal não são bloqueados; a regra vale para o agente.
