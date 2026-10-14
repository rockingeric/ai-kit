---
id: ADR-0021
title: Trava de branch segue cd e -C só numa lista do que é seguro
status: proposed
date: 2026-10-14
supersedes: null
superseded_by: null
body_sha: null
tags: [git, branches, hooks, seguranca]
summary: Hook segue cd/-C só na forma inequívoca; na dúvida, julga pela sessão
---
## Contexto

O hook `PreToolUse` do ADR-0019 julgava todo `git commit` pela branch do cwd da sessão. Com worktrees, isso barra commit legítimo (sessão na `main`, commit em `cd wt && git commit` numa branch de trabalho) e deixa passar `cd <checkout na main> && git commit` a partir de sessão em outra branch. O hook só vê o texto do comando, antes de ele rodar. Três revisões de segurança mostraram que seguir o texto com liberdade abre burlas confirmadas: subshell, `cd -`, `$OLDPWD`, `builtin`/`eval cd`, `source`, `export GIT_DIR`, `'~'` entre aspas, `#` no meio da palavra, `cd lnk/..`, `.ai/` plantada numa subpasta, e um `git` anterior que muda o alvo depois da checagem (`worktree add -f`, `init --separate-git-dir`, `switch --ignore-other-worktrees`).

## Opções

- **Sempre o cwd da sessão (como era)**: simples e sem burla nova, mas barra o fluxo de worktree e não vê o `cd` para o checkout na `main`.
- **Interpretar o comando como o shell (lista de bloqueio)**: cobre mais formas, mas cada leitura diferente do shell vira liberação; três rodadas de revisão acharam furos novos.
- **Lista do que é seguro, e na dúvida a sessão**: só segue a forma `cd <dir literal> && git [-C dir] <add|rm|mv|status|diff|log|show|commit> && git [-C dir] commit`; qualquer outra coisa volta ao cwd da sessão. Barra alguns commits legítimos em formas compostas.

## Decisão

Lista do que é seguro, e na dúvida a sessão: a dúvida nunca libera mais do que o comportamento anterior. A config vale para todo checkout do mesmo repo (mesmo git-common-dir) e vem do projeto da sessão, porque o worktree não tem `.ai/` (ela é excluída, não versionada). Um repo alheio só é julgado pela `.ai/project.yaml` no seu toplevel; uma `.ai/` numa subpasta é ignorada.

## Consequências

- Mais fácil: commit em worktree de branch de trabalho passa com a sessão na `main`; `cd <checkout na main> && git commit` é barrado.
- Mais difícil: formas compostas (`cd wt && npm test && git commit`, `;`, `$`, `#`, `~`) são julgadas pela sessão e podem barrar commit legítimo; o agente separa o comando em duas chamadas.
- Ampliar a lista (outro comando antes do commit, outro subcomando git) exige teste de burla em `tests/test_branches.py` e revisão de segurança: só entra o que não muda cwd, ambiente, HEAD, branch nem gitdir.
- `git()` tem timeout de 10s; se estourar, o hook não bloqueia (como já era para formas exóticas no ADR-0019).
