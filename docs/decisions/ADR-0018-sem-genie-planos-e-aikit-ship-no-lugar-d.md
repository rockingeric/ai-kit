---
id: ADR-0018
title: 'Sem Genie: planos e /aikit-ship no lugar do loop'
status: accepted
date: 2026-10-08
supersedes: null
superseded_by: null
body_sha: cb46f250dc293c306c9df480dbece977ad3d3bb0d8afbc0844e1bc031b7aecb3
tags: [genie, planos, gates]
summary: Genie fora; planos em .ai/plans e /aikit-ship como gate antes do PR
---
## Contexto

O plano previa integração opcional com o Genie, que roda o loop (brainstorm, wish, work, review, fix). Instalado (v6.261008.1), ele adiciona 18 skills globais ao contexto de toda sessão, em todo projeto, e três deles (review, council, docs) se sobrepõem às personas do kit. Os nomes de gate que o kit usava não existiam no Genie. Sem o loop, faltavam duas coisas: um plano que sobreviva entre sessões e um gate de revisão que não dependa de disciplina.

## Opções

- **Instalar o Genie junto no `aikit init`**: loop completo, mas custo de contexto fixo em todas as sessões e dois sistemas de revisão concorrentes.
- **Reimplementar o wish no kit**: duplica o Genie e puxa o kit para orquestração, fora do escopo.
- **Gateway que classifica todo pedido como ADR ou wish**: custo em todo pedido para acertar a minoria; a classificação nem é exclusiva.
- **Remover o Genie e cobrir as duas lacunas com peças pequenas**: planos em `.ai/plans/`, skill `/aikit-ship` acionado pelo humano, regra de decisão no bloco gerado do AGENTS.md.

## Decisão

Remover a integração com o Genie. Planos (`aikit plan new/done`, skill `aikit-plan`) guardam o trabalho entre sessões; ficam privados e só os abertos entram no índice. O `/aikit-ship` roda teste e lint e chama as personas de gate `ship` antes do PR. A escolha entre só fazer, ADR ou plano é uma regra de 4 linhas no bloco gerado, mais as descriptions dos skills; a checagem "decisão sem ADR" acontece uma vez por PR, no reviewer.

## Consequências

- Mais fácil: contexto fixo menor, um modelo mental só, e as regras do kit chegam a todos os projetos via `aikit build`.
- Mais difícil: sem execução autônoma e paralela de tarefas longas; o gate depende de o humano rodar `/aikit-ship`.
- Gates das personas passam a ser `plan`, `adr` e `ship`; `.genie/` sai do exclude.
