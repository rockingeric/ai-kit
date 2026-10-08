---
id: ADR-0020
title: Wishes com aprovação humana no lugar de planos
status: proposed
date: 2026-10-08
supersedes: null
superseded_by: null
body_sha: null
tags: [wishes, governanca, hooks]
summary: Wish nasce draft; humano aprova e só então nasce a branch wish/<slug>
---
## Contexto

O ADR-0018 trocou os wishes do Genie por "planos", com outro nome só para não confundir com o Genie. Com o Genie fora, o motivo do nome sumiu, e o humano prefere o conceito de wish. Faltava também um ponto do wish do Genie: o escopo é aprovado antes de o trabalho começar.

## Opções

- **Manter "plano" como está**: nenhum trabalho, mas contra a preferência do humano e sem aprovação de escopo.
- **Só renomear plano para wish**: barato, mas o agente continua começando a trabalhar num escopo que ninguém aprovou.
- **Wish com aprovação humana**: `draft` → `approved` → `done`; `aikit wish approve` exige critérios de aceite preenchidos e só então cria a branch `wish/<slug>`.

## Decisão

Wish com aprovação humana. Esta decisão altera a parte de planos do ADR-0018; o resto dele (Genie fora, `/aikit-ship`) continua valendo. O formato pega do wish do Genie o resumo, o escopo (entra e fica de fora), as decisões e os critérios, e deixa de fora os campos que serviam ao motor de orquestração dele. O hook `PreToolUse` passa a bloquear `aikit adr accept` e `aikit wish approve` quando quem roda é o agente; o humano roda no terminal ou com `!` no Claude Code. Planos antigos (a pasta plans dentro de .ai) geram aviso no lint com o caminho de migração.

## Consequências

- Mais fácil: o escopo de todo trabalho longo passa pelo humano antes de virar código, e a regra "só o humano decide" do ADR-0007 deixa de depender de o agente obedecer.
- Mais difícil: um comando a mais por wish; o bloqueio também barra o agente quando o humano pede em conversa para ele aceitar ou aprovar.
- O `aikit build` passa a remover skills que saíram do kit (o `aikit-plan` some sozinho dos projetos).
