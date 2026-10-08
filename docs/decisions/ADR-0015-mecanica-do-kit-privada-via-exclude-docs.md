---
id: ADR-0015
title: Mecânica do kit privada via exclude; docs/ vai no git
status: accepted
date: 2026-10-08
supersedes: ADR-0005
superseded_by: null
body_sha: f3be71e3f33146f54ba6ba3762213fd31d8f82132e7d8c22e3c48e8836d8d482
tags: [git, privacidade]
summary: Exclude só para a mecânica do kit
---
## Contexto

Com docs versionados, o exclude passa a cobrir só o maquinário.

## Opções

- **Excluir tudo**: perde o versionamento dos docs.
- **Excluir só a mecânica** (.ai/, subagents, skills, settings, CLAUDE.md e AGENTS.md criados pelo kit).

## Decisão

O bloco em `.git/info/exclude` lista só a mecânica; `docs/` é versionado.

## Consequências

- Mais fácil: o time vê o conhecimento, não o maquinário.
- Mais difícil: nada.
