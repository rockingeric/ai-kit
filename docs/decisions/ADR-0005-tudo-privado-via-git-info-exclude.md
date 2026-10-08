---
id: ADR-0005
title: Tudo privado via .git/info/exclude
status: superseded
date: 2026-10-08
supersedes: null
superseded_by: ADR-0015
body_sha: 19027cc6ae71f2e53281969d28fa0afee4447de0e8b8eddc5a7f82d010afee8c
tags: [git, privacidade]
summary: Tudo do kit fora do git via exclude
---
## Contexto

O kit não deve aparecer no repo do cliente nem mexer no .gitignore dele.

## Opções

- **.gitignore do projeto**: visível e versionado.
- **.git/info/exclude**: local, invisível ao time.

## Decisão

Tudo o que o kit instala, ADRs inclusive (salvo opt-in), vai para um bloco delimitado em `.git/info/exclude`.

## Consequências

- Mais fácil: instalar e remover sem rastro.
- Mais difícil: nada viaja com o clone.
