---
name: aikit-plan
description: Cria ou retoma um plano em .ai/plans para trabalho que atravessa várias sessões. Não use para tarefa que cabe numa sessão.
---

# Plano de trabalho

O plano guarda o estado de um trabalho longo, para que a próxima sessão retome sem reexplicação. É rascunho privado: o que tiver valor duradouro vira ADR (decisão) ou runbook (procedimento).

## Criar

1. `aikit plan new "Título no imperativo" --summary "até 80 caracteres"`. O comando imprime o caminho e cria a branch `plan/<slug>`, já fazendo a troca para ela; todo o trabalho do plano é commitado nela.
2. Preencha, curto:
   - **Objetivo**: o resultado em 1 ou 2 frases.
   - **Escopo**: o que entra e o que fica de fora (no mínimo 1 item fora).
   - **Critérios de aceite**: verificáveis, cada um vira teste ou comando. São o que o `/aikit-ship` e o `aikit-qa` conferem.
   - **Passos**: em ordem, cada um pequeno o bastante para uma parte de sessão.
3. Decisão estrutural que surgir no planejamento → skill `aikit-adr`, e o id vai em `adrs:` no frontmatter.

## Retomar (sessão nova)

1. O índice lista os planos `active`. Abra só o plano da tarefa.
2. Confira que está na branch `plan/<slug>`; se não estiver, `git switch plan/<slug>`.
3. Comece pela seção "Próxima sessão".

## Antes de encerrar a sessão

Marque os passos feitos (`- [x]`) e reescreva "Próxima sessão" em até 5 linhas: onde parou, o que falta e armadilhas encontradas.

## Concluir

Quando todos os critérios estiverem marcados e o `/aikit-ship` aprovar: `aikit plan done <slug>`.
