# Overlay de exemplo

Um overlay adiciona regras de domínio (LGPD, PCI, saúde...) às personas base, sem copiar as personas.

## Como criar

1. Copie esta pasta para `overlays/<nome>/` no repo do kit.
2. Em `personas/<id>.yaml`, escreva só o que muda. Listas (`principles`, `never`, `tools`, `reads`, `gates`) somam às da base; escalares (`model`, `role`, `description`) substituem.
3. No projeto: `aikit init --overlay <nome>` (ou adicione o nome em `.ai/overlays.yaml`) e rode `aikit build`.

Ordem do merge: base do kit → overlays na ordem de `.ai/overlays.yaml` → override do projeto em `.ai/personas/<id>.yaml`.

Cada linha adicionada custa tokens em toda delegação para aquela persona. O `aikit lint` avisa quando uma persona compilada passa de 40 linhas.
