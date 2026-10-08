---
id: ADR-0003
title: ADR é markdown com frontmatter YAML (MADR)
status: accepted
date: 2026-10-08
supersedes: null
superseded_by: null
body_sha: 13595ba952f3be424e89ef34ca67b686d20212d8f727a04609712f55d4e8b447
tags: [adr, formato]
summary: 'ADR em MADR: humano lê no GitHub, build lê o cabeçalho'
---
## Contexto

ADRs são lidos por humanos em PRs e pelo build para montar o índice.

## Opções

- **ADR em YAML puro**: fácil de parsear, ruim de ler e revisar.
- **Markdown com frontmatter**: o GitHub renderiza o corpo; o build lê só o cabeçalho.

## Decisão

MADR: frontmatter com id, status, datas, ligações e summary; corpo com Contexto, Opções, Decisão e Consequências.

## Consequências

- Mais fácil: revisão em PR e indexação barata.
- Mais difícil: o frontmatter precisa de schema (adr-frontmatter.json).
