---
name: aikit-ship
description: Gate antes do PR - roda testes e lint, chama as personas de revisão e devolve o veredito.
disable-model-invocation: true
---

# Gate antes do PR

Objetivo: nenhuma entrega vai para PR sem teste, lint e revisão. Seja econômico: as personas leem o diff, não o repo.

## Passos

1. **Branch**: `git branch --show-current`. Se for a branch padrão do projeto (`git.default_branch` em `.ai/project.yaml`, ou a de `origin/HEAD`, ou `main`), pare com BLOQUEADO: o trabalho precisa de branch própria (`git switch -c <tipo>/<slug>`, ou `wish/<slug>` se houver wish). Se a branch for `wish/<slug>` e o wish não estiver `approved`, também BLOQUEADO: o humano precisa aprovar antes.
2. **Mecânico, sem subagent**: rode os comandos `test` e `lint` de `.ai/project.yaml` e depois `aikit lint`. Se algo falhar, pare aqui com o veredito CORRIGIR e a saída do erro.
3. **Escopo**: `git diff --stat <branch padrão>...HEAD` mais as mudanças não commitadas. Guarde a lista de arquivos.
4. **Revisão em paralelo**, passando a cada persona só a lista de arquivos e o objetivo da mudança:
   - `aikit-reviewer`: sempre.
   - `aikit-security`: só se o diff tocar auth, sessão, permissões, entrada externa, SQL ou shell, segredos, criptografia ou dependências.
   - `aikit-qa`: se houver wish `approved` desta branch, para conferir os critérios de aceite dele; senão, só se o diff mudar comportamento sem teste novo.
5. **Decisões**: no índice, há ADR `proposed`? Liste-os; o humano decide antes do merge. O diff introduz decisão estrutural sem ADR (o reviewer aponta)? Proponha criar com o skill `aikit-adr`.
6. **Wish**: se houver wish `approved` desta branch e todos os critérios estiverem atendidos, sugira `aikit wish done <slug>`.

## Fim

```
Veredito: PODE ABRIR PR | CORRIGIR | BLOQUEADO
Testes/lint: ok | falhou (comando)
Achados: <do mais grave ao menos grave, arquivo:linha, uma linha cada>
Pendências do humano: <ADRs proposed, critérios abertos>
```
