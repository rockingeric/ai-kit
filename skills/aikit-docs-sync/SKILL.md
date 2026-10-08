---
name: aikit-docs-sync
description: Confere se docs, runbooks e ADRs ainda batem com o código e propõe correções, sem aplicá-las.
disable-model-invocation: true
---

# Sincronizar docs com o código

Delegue à persona `aikit-tech-writer`. Ela propõe as correções; o humano decide.

## Passos

1. Rode `aikit lint --refs`. Ele lista, sem custo de leitura, os paths citados que não existem mais e os runbooks com verificação vencida.
2. Abra só os docs que o lint apontou. Para cada um, confira também os comandos citados contra `.ai/project.yaml` → `commands`.
3. Para cada divergência, proponha a correção como diff curto. Não edite nada ainda.
4. ADR `accepted` não se corrige: se ele citar algo que mudou, proponha um ADR novo (skill `aikit-adr`) ou deixe como registro histórico.
5. Runbook revisado e confirmado pelo humano: `aikit runbook verify <slug>`.

## Fim

Uma tabela com doc, problema e correção proposta, seguida de "Aplicar? (todas / números / nenhuma)".
