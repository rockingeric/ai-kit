---
id: ADR-0023
title: Abrir o worktree do wish ao lado do repo
status: accepted
date: 2026-10-17
supersedes: ADR-0022
superseded_by: null
body_sha: d694f75fda7b376be0650293f043d40a51a4fefa08594abda2d2abad359fc66e
tags: [git, branches, wishes, worktrees]
summary: wish approve cria wt-<iniciais>-<slug> na pasta que contém o repo
---
## Contexto

O ADR-0022 abre o worktree do wish na "pasta-pai da pasta que contém o repo" (`main.parent.parent`), supondo que todo repo mora em `~/Projetos/<repo>`. Nem todo layout é assim: em `~/code/<workspace>/<repo>` (ex.: `~/code/hapvida/hap-content-agent`), a pasta do repo é um workspace com vários projetos, e o worktree cai em `~/code/wt-hca-<slug>`, a pasta que reúne os workspaces, longe do projeto. Nesse workspace os worktrees abertos à mão já ficam ao lado do repo (`~/code/hapvida/wt-core-*`, `wt-sig-*`, `wt-hca-*`). O que o kit não sabe de antemão é a profundidade do layout: repo solto, workspace, workspace dentro de pasta de código.

## Opções

- **Pasta-pai da pasta do repo (como é)**: tira o worktree da pasta de projetos quando o layout é plano, mas depende de profundidade fixa; com workspaces, cai fora do workspace.
- **Home quando o repo está sob `~`**: independe da profundidade, mas espalha `wt-*` no home e separa o worktree do workspace onde o projeto mora.
- **Pasta fixa (`~/worktrees`)**: um lugar só, mas mistura worktrees de todos os workspaces e esconde a relação com o projeto.
- **Ao lado do repo (pasta que contém o repo)**: independe da profundidade e fica no workspace do projeto, como já se faz à mão; o custo é um `wt-*` a mais na pasta de projetos para quem tem layout plano (`~/Projetos/wt-ak-<slug>`).

## Decisão

O worktree do wish abre ao lado do repo: `<pasta que contém o repo>/wt-<iniciais>-<slug>`, porque é a única regra que acerta o workspace em qualquer profundidade. `git.worktree_dir` continua trocando a pasta. O resto do ADR-0022 vale sem mudança: opt-in via `git.worktrees: true`, iniciais, branch `wish/<slug>`, reuso, erro em caminho ocupado, provisionamento com o kit em symlink e `index.yaml` local, sessão nova, `wish done` só remove worktree limpo e nunca com `--force`.

## Consequências

- Mais fácil: o worktree fica no workspace do projeto (`~/code/hapvida/wt-hca-<slug>`), junto dos que já existem, sem configurar `git.worktree_dir`.
- Mais difícil: em layout plano, a pasta de projetos ganha `wt-*` (o que o ADR-0022 queria evitar); quem não quiser define `git.worktree_dir`.
- Iniciais colidem dentro do workspace, onde os nomes se parecem (`hap-content-agent` e `hap-campaign-taxonomy` → `hca`); só há erro se o mesmo slug se repetir, e o erro de caminho ocupado continua cobrindo.
- Muda: `worktree.target` passa a usar `main.parent`; o teste do lugar padrão e o README/docs que citam `~/wt-` acompanham. Worktrees já criados não se movem: o reuso acha pela `git worktree list`.
