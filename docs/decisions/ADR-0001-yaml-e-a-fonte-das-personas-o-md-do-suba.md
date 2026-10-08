---
id: ADR-0001
title: YAML é a fonte das personas; o .md do subagent é gerado
status: accepted
date: 2026-10-08
supersedes: null
superseded_by: null
body_sha: 0ac7211b2f623434735afb864e289ad6958c736956e78e00a4d55a46f5517fcb
tags: [personas, build]
summary: Personas em YAML, compiladas para .claude/agents
---
## Contexto

O Claude Code só lê subagents em markdown com frontmatter. Precisamos validar personas, aplicar overlays de domínio e overrides por projeto sem copiar arquivos.

## Opções

- **Escrever o .md à mão**: zero ferramenta, mas sem schema, sem merge e cópia divergente em cada projeto.
- **YAML como fonte, .md gerado**: schema, lint e merge de camadas; custa um passo de build.

## Decisão

YAML é a fonte. `aikit build` gera `.claude/agents/aikit-*.md` com cabeçalho de não editar.

## Consequências

- Mais fácil: validar, mesclar overlays e atualizar todos os projetos com um build.
- Mais difícil: quem edita o .md gerado perde a edição; o cabeçalho e o doctor avisam.
