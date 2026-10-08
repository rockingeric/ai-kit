---
id: ADR-0014
title: ADRs e runbooks versionados em docs/ por padrão
status: accepted
date: 2026-10-08
supersedes: ADR-0004
superseded_by: null
body_sha: 07edc9d1cc92ceba901da955472236c9f3da4dc19cb752fe67c73fc424bb4ae8
tags: [adr, docs, git]
summary: Conhecimento do projeto vai para o git do time
---
## Contexto

Na prática, ADRs privados se perdiam em clones novos e não serviam ao time. O conhecimento do projeto pertence ao time.

## Opções

- **Manter privado com opt-in**.
- **Versionar por padrão em docs/**, aceitando que o setup aparece nos PRs.

## Decisão

ADRs e runbooks vivem em `docs/` e são versionados. `paths.adr` e `paths.runbooks` só mudam se o projeto já tiver outra convenção.

## Consequências

- Mais fácil: o clone carrega as decisões; o backup encolhe para o .ai/.
- Mais difícil: ADR proposed de agente fica visível até ser aceito ou descartado.
