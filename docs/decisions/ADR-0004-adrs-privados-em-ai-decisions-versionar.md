---
id: ADR-0004
title: ADRs privados em .ai/decisions; versionar é opt-in
status: superseded
date: 2026-10-08
supersedes: null
superseded_by: ADR-0014
body_sha: 9b01d4841f4a9b9e514b9ebf507291b129aa43eec348742b0edcc019b27bd1a1
tags: [adr, privacidade]
summary: ADRs fora do git do cliente por padrão
---
## Contexto

O kit nasceu como ferramenta pessoal para projetos de clientes, e ADR no git do cliente expõe o setup em todo PR.

## Opções

- **Privado por padrão, opt-in por projeto via paths.adr**.
- **Versionado por padrão**.

## Decisão

ADRs em `.ai/decisions/`, fora do git; versionar é opt-in via `paths.adr`.

## Consequências

- Mais fácil: nada do kit aparece para o cliente.
- Mais difícil: clone novo perde os ADRs; exige backup.
