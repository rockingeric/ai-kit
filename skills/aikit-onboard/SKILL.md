---
name: aikit-onboard
description: Preenche .ai/project.yaml e .ai/AGENTS.md lendo o repo. Rodar uma vez, logo depois do `aikit init`.
disable-model-invocation: true
---

# Onboard do ai-kit

Objetivo: deixar `.ai/project.yaml` e `.ai/AGENTS.md` reais e enxutos. O AGENTS.md entra em toda sessão, então cada linha custa tokens para sempre.

## Passos

1. Leia só os arquivos de manifesto e configuração que existirem, sem varrer o código:
   `README*` (primeiras 60 linhas), `package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `Makefile`, `justfile`, `docker-compose*`, `.github/workflows/*`, configs de lint e teste.
2. Preencha `.ai/project.yaml` (schema em `aikit lint`): `name`, `description` (1 frase), `stack`, `commands` (test, lint, run, build, só os que existem e que você confirmou no manifesto), `conventions` (no máximo 5, só as que não são óbvias pelo lint), `paths.src` e `paths.tests`. Não mude `paths.adr` nem `paths.runbooks` sem o humano pedir.
3. Reescreva as seções de `.ai/AGENTS.md` acima do bloco `<!-- aikit:personas:start -->`, trocando todo `TODO`:
   - Projeto: 1 ou 2 frases.
   - Comandos: os mesmos do project.yaml.
   - Convenções: só o que um agente erraria sem saber.
   - Mantenha a seção "Como trabalhar aqui" e não toque no bloco gerado.
   - Total do arquivo: no máximo 60 linhas.
4. Rode `aikit build` e depois `aikit lint`. Corrija o que o lint apontar.
5. Se o repo já tem decisões claras (ex.: ORM escolhido, monorepo), não escreva ADRs agora; liste-as para o humano decidir se viram ADR via skill `aikit-adr`.

## Fim

Responda em até 8 linhas: o que preencheu, os comandos confirmados, o que ficou em dúvida e as decisões candidatas a ADR.
