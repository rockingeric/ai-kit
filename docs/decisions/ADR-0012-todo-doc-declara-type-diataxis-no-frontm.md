---
id: ADR-0012
title: Todo doc declara type Diátaxis no frontmatter
status: superseded
date: 2026-10-08
supersedes: null
superseded_by: ADR-0017
body_sha: 7dd30f4045e543209f85a76ee8e7c90c5c5151f85c347caba46e3d2697a46ba1
tags: [docs, diataxis]
summary: type Diátaxis obrigatório no frontmatter de todo doc
---
## Contexto

Cada persona deve ler só o tipo de doc que importa.

## Opções

- **type no frontmatter de todo doc**.
- **Tipo inferido da pasta**.

## Decisão

Todo doc e runbook declara `type:`; o índice agrupa por tipo.

## Consequências

- Mais fácil: agrupamento explícito.
- Mais difícil: frontmatter repetitivo em todo arquivo.
