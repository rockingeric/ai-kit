---
id: ADR-0017
title: Tipo Diátaxis inferido da pasta
status: accepted
date: 2026-10-08
supersedes: ADR-0012
superseded_by: null
body_sha: 3439b02c5972f649a6ddb6f3603273d815e380b68c2b0523c9877eeda32dd565
tags: [docs, diataxis]
summary: 'Pasta define o tipo; type: só para exceção e .ai/docs'
---
## Contexto

Com pastas por tipo em docs/, declarar `type:` em todo arquivo é redundante.

## Opções

- **type: em todo doc**.
- **Tipo pela pasta**: decisions e architecture = explanation, runbooks = how-to, reference = reference, guides = tutorial.

## Decisão

O tipo vem da pasta. `type:` só em exceções e em `.ai/docs/` (que não tem pastas tipadas); o lint acusa contradição.

## Consequências

- Mais fácil: menos frontmatter para manter.
- Mais difícil: doc fora das pastas tipadas não entra no índice.
