---
id: ADR-0002
title: O ganho de contexto vem do índice, não do formato
status: accepted
date: 2026-10-08
supersedes: null
superseded_by: null
body_sha: fe42506c3850e9b150bab9fba5bb768be312e82bb6ede7bbe0079e9e7751b5d9
tags: [contexto, tokens]
summary: index.yaml como porta de entrada; o formato dos docs não importa
---
## Contexto

YAML e markdown custam parecido em tokens. O custo real de contexto vem de o agente abrir arquivos demais para achar o que importa.

## Opções

- **Converter docs para um formato mais compacto**: ganho marginal, perde legibilidade humana.
- **Índice gerado com resumos de uma linha**: o agente lê ~2k tokens e abre só o necessário.

## Decisão

Um `.ai/index.yaml` gerado é a porta de entrada. Docs continuam em markdown.

## Consequências

- Mais fácil: orçar contexto (o lint cobra ~2k tokens para o índice).
- Mais difícil: o índice precisa estar sempre em dia; build implícito e hook garantem isso.
