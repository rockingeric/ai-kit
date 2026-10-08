---
name: aikit-adr
description: Registra uma decisão de arquitetura como ADR proposed (de uma conversa ou da síntese do council).
---

# Registrar ADR

Um ADR registra uma decisão e o porquê. Nasce `proposed`; só o humano aceita.

## Passos

1. Confira em `.ai/index.yaml` (seção `decisions`) se já existe ADR sobre o tema. Se um ADR `accepted` for contrariado, este ADR o substitui: use `--supersedes`.
2. Crie o arquivo:
   `aikit adr new "Título curto no imperativo" --tags tag1,tag2 --summary "até 80 caracteres" [--supersedes NNNN]`
   O comando imprime o caminho do arquivo.
3. Preencha as quatro seções, curtas:
   - **Contexto**: o problema e as restrições, em fatos (números, prazos, limites).
   - **Opções**: no mínimo 2, cada uma com custo e benefício.
   - **Decisão**: a escolhida, em uma frase, e o motivo principal.
   - **Consequências**: o que fica mais fácil, o que fica mais difícil, o que precisa mudar.
4. Não altere o frontmatter, salvo `tags` e `summary`. Nunca rode `aikit adr accept`.

## Fim

Termine com exatamente estas linhas:

```
ADR-NNNN proposed: <decisão em uma frase>
Para aceitar: aikit adr accept NNNN
```
