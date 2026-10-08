---
id: ADR-0006
title: Tudo do kit dentro de .ai/, exceto caminhos fixos das ferramentas
status: accepted
date: 2026-10-08
supersedes: null
superseded_by: null
body_sha: c7bc18a129175528bdb9c1cc999a5dcf2faae0f7aac35a3b188c59e6959c56fa
tags: [estrutura]
summary: Uma pasta .ai/ para instalar, remover e fazer backup
---
## Contexto

Espalhar arquivos pelo repo dificulta remover e fazer backup.

## Opções

- **Arquivos soltos na raiz**.
- **Uma pasta .ai/**, com exceção do que as ferramentas exigem em caminho fixo (.claude/, CLAUDE.md, AGENTS.md).

## Decisão

Tudo do kit vive em `.ai/`; o resto é gerado ou copiado e listado no manifesto.

## Consequências

- Mais fácil: backup é copiar uma pasta; uninstall é ler o manifesto.
- Mais difícil: arquivos de caminho fixo precisam de registro no manifesto.
