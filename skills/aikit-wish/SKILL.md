---
name: aikit-wish
description: Cria ou retoma um wish em .ai/wishes para trabalho que atravessa várias sessões. Não use para tarefa que cabe numa sessão.
---

# Wish

Um wish define o escopo de um trabalho longo e guarda o estado dele entre sessões. Nasce `draft`; só o humano aprova, e só então o trabalho começa. É rascunho privado: o que tiver valor duradouro vira ADR (decisão) ou runbook (procedimento).

## Criar (draft)

1. `aikit wish new "Título no imperativo" --summary "até 80 caracteres"`. O comando imprime o caminho.
2. Preencha, curto:
   - **Resumo**: o resultado em 2 ou 3 frases e por que importa.
   - **Escopo**: o que entra e o que fica de fora (no mínimo 1 item fora).
   - **Decisões**: escolhas locais deste wish. Decisão estrutural → skill `aikit-adr`, e o id vai em `adrs:` no frontmatter.
   - **Critérios de aceite**: verificáveis, cada um vira teste ou comando. São o que o `/aikit-ship` e o `aikit-qa` conferem. Sem critério preenchido o wish não pode ser aprovado.
   - **Passos**: em ordem, cada um pequeno o bastante para uma parte de sessão.
3. Pare e peça a aprovação, terminando com exatamente:

```
Wish <slug> em draft. Revise .ai/wishes/<slug>.md e, se concordar: aikit wish approve <slug>
```

Não implemente nada antes da aprovação. O agente não consegue rodar `aikit wish approve` (bloqueado); quem aprova é o humano.

## Retomar (sessão nova)

1. O índice lista os wishes `approved` (em andamento) e `draft` (aguardando aprovação). Abra só o wish da tarefa.
2. Confira que está na branch `wish/<slug>`; se não estiver, `git switch wish/<slug>`.
3. Comece pela seção "Próxima sessão".

## Antes de encerrar a sessão

Marque os passos feitos (`- [x]`) e reescreva "Próxima sessão" em até 5 linhas: onde parou, o que falta e armadilhas encontradas.

## Concluir

Quando todos os critérios estiverem marcados e o `/aikit-ship` aprovar: `aikit wish done <slug>`.
