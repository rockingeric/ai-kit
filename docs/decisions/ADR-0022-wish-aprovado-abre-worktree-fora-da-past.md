---
id: ADR-0022
title: Wish aprovado abre worktree fora da pasta de projetos
status: accepted
date: 2026-10-14
supersedes: null
superseded_by: null
body_sha: 20c8ea7c2eaf89d93e6e7e0dfbee21701a6e177d5681089148dcb067c79b853a
tags: [git, branches, wishes, worktrees]
summary: wish approve cria worktree wt-<iniciais>-<slug> com o kit em symlink
---
## Contexto

Hoje `aikit wish approve` roda `git switch [-c] wish/<slug>` no checkout atual (`Project.ensure_branch`). Com mais de um wish aberto, o humano e o agente disputam o mesmo checkout: trocar de wish exige commit ou stash, e a sessão da `main` some. O ADR-0019 descartou "worktree por tarefa" porque pesa em quem trabalha num checkout só; por wish, que já é trabalho de várias sessões, o custo compensa. Um worktree novo não tem o kit: `.ai/`, `CLAUDE.md`, `AGENTS.md` e os `aikit-*` de `.claude/` são excluídos via `.git/info/exclude` (ADR-0015). O exclude fica no git-common-dir e vale para todos os worktrees, e o hook do ADR-0021 já julga commit em worktree pelo git-common-dir.

## Opções

- **`git switch` no checkout atual (como é)**: zero mudança, mas um wish por vez por checkout.
- **Worktree dentro do repo (`.worktrees/<slug>`)**: fácil de achar, mas aninha um checkout no outro; ferramentas (pytest, ripgrep, watchers) varrem os dois.
- **Worktree fora da pasta de projetos, com o kit em symlink**: `~/wt-<iniciais>-<slug>` para um repo em `~/Projetos/<repo>`; não polui a pasta de projetos nem o repo, mas é um diretório a mais no home e uma sessão nova do Claude por wish.
- **Copiar o kit para o worktree em vez de symlink**: worktree independente, mas wishes e personas divergem; aprovar ou concluir um wish num lado não aparece no outro.
- **Ligado por padrão vs opt-in (`git.worktrees` no `project.yaml`)**: ligado por padrão muda o comportamento de quem só atualiza o kit e cria pastas fora do repo sem ter pedido; opt-in mantém o `git switch` do ADR-0020 para quem não liga a chave.

## Decisão

Worktree fora da pasta de projetos, com o kit em symlink, opt-in via `git.worktrees: true`. Sem a chave, `approve` continua no `git switch`. Esta decisão altera só onde a branch do ADR-0020 é aberta; o resto dele (wish `draft` → `approved` → `done`, critérios exigidos, approve só do humano) continua valendo. Também revê, para wishes, a opção "worktree por tarefa" descartada no ADR-0019; as três camadas daquele ADR continuam.

- **Lugar e nome**: pasta-pai da pasta que contém o repo (repo em `~/Projetos/ai-kit` → `~/wt-ak-<slug>`). Iniciais: primeira letra de cada parte do nome da pasta do repo, separando por `-`, `_`, `.` e espaço (`ai-kit` → `ak`). `git.worktree_dir` troca a pasta-pai (uma chave, custo baixo). A branch continua `wish/<slug>`.
- **Reuso**: se a branch já está num worktree (`git worktree list`), usa esse caminho; se a branch existe sem worktree, `git worktree add <path> wish/<slug>`; senão, `-b wish/<slug>` a partir do HEAD. Caminho ocupado por algo que não é worktree deste repo (iniciais repetidas entre projetos) é erro, nunca sobrescrita.
- **Provisionamento**: no worktree, `.ai/` é uma pasta de verdade com cada item em symlink para o checkout principal, exceto `index.yaml`, que o `aikit build` gera localmente (os ADRs e docs são versionados e diferem por branch; um índice compartilhado ficaria com a visão de quem rodou o build por último). Os demais arquivos do kit listados no manifesto (`CLAUDE.md`, `AGENTS.md`, `.claude/settings.local.json`, cada `aikit-*` de `.claude/agents` e `.claude/skills`) viram symlink um a um. Pasta e não symlink para `.ai/` porque o padrão `/.ai/` do exclude só casa diretório: um symlink `.ai` aparece como não rastreado (testado).
- **Sessão**: o CLI não move a sessão do Claude; `approve` imprime o caminho e `cd <path> && claude`.
- **Fim**: `aikit wish done` oferece `git worktree remove <path>` só se `git status --porcelain` do worktree estiver vazio; sujo, diz o que ficou e mantém. Nunca `--force`; a branch fica para o PR. O `remove` apaga os symlinks sem seguir o alvo (testado).

## Consequências

- Mais fácil: vários wishes em paralelo, cada um com sua sessão, e a `main` livre no checkout principal; wishes, personas e hooks têm uma fonte só.
- Mais difícil: um diretório por wish fora do repo, que o humano precisa abrir numa sessão nova; o provisionamento segue o manifesto, então arquivo novo do kit exige entrada lá. Rodar `aikit init` ou editar persona dentro do worktree mexe no checkout principal (é o mesmo arquivo).
- O ADR-0021 parte de "o worktree não tem `.ai/`"; com o provisionamento passa a ter, e a config é a mesma (symlink para o principal), então a regra dele não muda.
- Iniciais podem colidir entre projetos (`ai-kit` e `api-kernel` → `ak`); o erro de caminho ocupado cobre o caso, e `git.worktree_dir` separa por projeto se incomodar.
