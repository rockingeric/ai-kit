---
id: ADR-0007
title: ADR de agente nasce proposed; só o humano aceita
status: accepted
date: 2026-10-08
supersedes: null
superseded_by: null
body_sha: 21a6bcc6720da7ef5eece5797796d0c62b85f3f0412d6090cc5eec48ab925649
tags: [adr, governanca]
summary: Agente propõe; só humano aceita (aikit adr accept ou PR)
---
## Contexto

Agentes tomam decisões em conversas e no council. Registrar isso como decisão do projeto sem revisão humana é perigoso.

## Opções

- **Agente escreve accepted direto**.
- **Agente escreve proposed; humano aceita**, gravando body_sha para congelar o corpo.

## Decisão

ADR de agente nasce `proposed`. `aikit adr accept` (humano) grava `body_sha`; o corpo vira imutável e o lint confere.

## Consequências

- Mais fácil: confiança no que está accepted.
- Mais difícil: um passo manual por decisão; o skill aikit-adr imprime o comando pronto.
