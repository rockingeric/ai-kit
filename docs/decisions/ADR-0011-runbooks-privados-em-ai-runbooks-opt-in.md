---
id: ADR-0011
title: Runbooks privados em .ai/runbooks; opt-in via paths.runbooks
status: superseded
date: 2026-10-08
supersedes: null
superseded_by: ADR-0016
body_sha: a199fea4e7ce4f7f999dc57b5fe110ea796aa823c9a88a4cf02afe15ac3cb14c
tags: [runbooks, privacidade]
summary: Runbooks seguem a regra dos ADRs privados
---
## Contexto

Mesmo critério de exposição dos ADRs.

## Opções

- **Privado com opt-in**.
- **Versionado**.

## Decisão

Runbooks em `.ai/runbooks/`, opt-in via `paths.runbooks`.

## Consequências

- Mais fácil: consistência com os ADRs.
- Mais difícil: runbook serve ao time às 3 da manhã, e privado não cumpre isso.
