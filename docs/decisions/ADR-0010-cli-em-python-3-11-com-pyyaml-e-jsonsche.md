---
id: ADR-0010
title: CLI em Python 3.11+ com PyYAML e jsonschema
status: accepted
date: 2026-10-08
supersedes: null
superseded_by: null
body_sha: a8be65d5a1f93ada2787f89a66baf0ab969370b3ed09610f0ad38a802cc97c7d
tags: [cli, stack]
summary: CLI Python, instalado com pipx em modo editável
---
## Contexto

O CLI precisa ler YAML, validar schemas e mexer em arquivos; deve ser simples de testar.

## Opções

- **Node/TypeScript**: bom ecossistema, mais build.
- **Python + PyYAML + jsonschema**: duas dependências, pytest, sem servidor.

## Decisão

Python 3.11+, instalado com `pipx install -e ~/ai-kit` (ou `uv tool install -e`).

## Consequências

- Mais fácil: testes rápidos e dados do kit lidos direto do clone.
- Mais difícil: exige Python na máquina.
