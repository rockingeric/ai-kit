---
id: ADR-0009
title: Personas base vivem no kit; o projeto guarda só overrides
status: accepted
date: 2026-10-08
supersedes: null
superseded_by: null
body_sha: b485a7930d6bf150e7d694d5ab7fc1d2f487e95b8c9e8296cb709785229a15d1
tags: [personas, atualizacao]
summary: Base no kit, override no projeto; git pull + build atualiza tudo
---
## Contexto

Copiar personas para cada projeto gera deriva e torna atualizações manuais.

## Opções

- **Cópia por projeto**.
- **Base no kit + override parcial no projeto**, com versão do kit gravada no manifesto.

## Decisão

Personas base vivem no kit. O projeto guarda só `.ai/personas/<id>.yaml` com o que muda. O doctor compara versões.

## Consequências

- Mais fácil: `git pull` no kit + `aikit build` atualiza personas e skills.
- Mais difícil: mudança na base afeta todos os projetos no próximo build.
