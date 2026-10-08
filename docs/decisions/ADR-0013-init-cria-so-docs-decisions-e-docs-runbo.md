---
id: ADR-0013
title: init cria só docs/decisions e docs/runbooks
status: accepted
date: 2026-10-08
supersedes: null
superseded_by: null
body_sha: 78cc5fda9f5ccb6f9ea32809ab6181fed9df20cbf76c37f15d0a9f7c0f5eba28
tags: [docs, init]
summary: Pastas de docs nascem com o primeiro doc, exceto decisions e runbooks
---
## Contexto

Com docs versionados, pastas vazias aparecem como ruído no primeiro PR e parecem documentação abandonada.

## Opções

- **Criar as 5 pastas no init**.
- **Criar só as que o fluxo usa no dia 1**; architecture, reference e guides nascem sob demanda.

## Decisão

`aikit init` cria só `docs/decisions/` e `docs/runbooks/`, sem .gitkeep.

## Consequências

- Mais fácil: PR inicial limpo.
- Mais difícil: quem cria o primeiro doc de outro tipo cria a pasta (a persona tech-writer sabe).
