---
id: ADR-0016
title: Runbooks em docs/runbooks, versionados
status: accepted
date: 2026-10-08
supersedes: ADR-0011
superseded_by: null
body_sha: db56b2639b78f486a045ca10dcfa7fe2cc5c3473d860c975adad917411aa1d5e
tags: [runbooks, docs]
summary: Runbook é do time; vai para o git
---
## Contexto

Runbook existe para o time agir num incidente. Privado, ele não cumpre esse papel.

## Opções

- **Privado**.
- **Versionado em docs/runbooks/**.

## Decisão

Runbooks em `docs/runbooks/`, criados com `aikit runbook new`, com `last_verified` cobrado pelo lint.

## Consequências

- Mais fácil: o runbook está onde o time procura.
- Mais difícil: nada.
