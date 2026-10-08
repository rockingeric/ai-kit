---
id: ADR-0008
title: Máximo 5 personas; o dev é a thread principal
status: accepted
date: 2026-10-08
supersedes: null
superseded_by: null
body_sha: 4bc553fcd38926cbc8274d79b044a6a770f9d6facf385f55508604715d4780ae
tags: [personas, tokens]
summary: Cinco personas; o dev é a thread principal do Claude
---
## Contexto

Cada subagent soma sua description ao contexto fixo e disputa a auto-delegação.

## Opções

- **Uma persona por papel imaginável**: polui a delegação e custa tokens.
- **Cinco revisores/consultores; o dev é a sessão principal**.

## Decisão

No máximo 5 personas: architect, reviewer, security, qa, tech-writer. O lint avisa acima disso.

## Consequências

- Mais fácil: delegação previsível e contexto fixo pequeno.
- Mais difícil: papel novo precisa substituir um existente ou desligá-lo (`enabled: false`).
