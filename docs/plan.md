# ai-kit: plano de implementação

Oct 8, 2026 · @Eric

> Snapshot exportado do doc em https://claude.ai/code/artifact/d51060d6-ddf2-4197-97d8-bb0ef0b307ba (rev 44). O doc é a fonte principal.
> **Pendente de sync**: revisão de 8 Out 2026 aplicada só neste arquivo (o doc não estava acessível); replicar lá.
> **Status (8 Out 2026)**: fases 1 a 6 implementadas e testadas (49 testes); Genie substituído por wishes e /aikit-ship (ADR-0018, ADR-0020); uma branch por trabalho imposta (ADR-0019); fase 7 (piloto) pendente.

## Objetivo e escopo

O ai-kit é um repo seu, clonado uma vez na máquina, que instala em qualquer projeto um setup de personas, ADRs e contexto enxuto para coding agents. A mecânica do kit (`.ai/`, subagents, skills, hook) fica privada, fora do git do cliente. O conhecimento do projeto — ADRs, runbooks e docs — vive em `docs/`, versionado no git: pertence ao time e viaja com o clone.

**Dentro do escopo (v1)**

- 5 personas genéricas, definidas em YAML e compiladas para subagents do Claude Code
- ADRs em `docs/decisions/` (markdown com frontmatter YAML), versionados no git do projeto
- Runbooks em `docs/runbooks/`, versionados; `docs/architecture|reference|guides/` nascem sob demanda
- Docs classificados pelos 4 tipos do Diátaxis (tutorial, how-to, reference, explanation), tipo inferido da pasta, índice agrupado por tipo
- Um `index.yaml` que o agente lê primeiro, para abrir só o que precisa
- CLI `aikit` para instalar, compilar, validar e remover
- 3 skills e 1 hook do Claude Code
- Wishes em `.ai/wishes/` para trabalho que atravessa sessões, aprovados pelo humano antes de começar, e o gate `/aikit-ship` antes do PR (substituem a integração com o Genie; ADR-0018 e ADR-0020)

**Fora do escopo (v1)**

- Distribuição como plugin do marketplace (fica para v2)
- Suporte a Windows nativo
- Overlays de domínio prontos (só o mecanismo e um exemplo vazio)

## Decisões já tomadas

Estas viram os primeiros ADRs do próprio ai-kit (dogfooding). As versões originais de 4, 5 e 11 ("privado por padrão, versionar é opt-in") foram supersedidas em 8 Out 2026 — os ADRs do kit registram as duas versões.

| # | Decisão | Por quê |
| --- | --- | --- |
| 1 | YAML é a fonte das personas; `.claude/agents/*.md` é gerado | Claude Code exige `.md`; YAML dá schema, lint e merge de overlays |
| 2 | Ganho de contexto vem do `index.yaml`, não do formato | YAML e MD custam parecido em tokens; o ganho é abrir menos arquivos |
| 3 | ADR = markdown com frontmatter YAML (MADR) | Humano lê no GitHub; o build lê só o cabeçalho |
| 4 | ADRs e runbooks versionados em `docs/` por padrão | Conhecimento do projeto pertence ao time e viaja com o clone; o custo aceito é o setup aparecer nos PRs |
| 5 | Mecânica do kit privada via `.git/info/exclude`; `docs/` vai no git | O time vê o conhecimento, não o maquinário; e não mexe no `.gitignore` dele |
| 6 | Tudo do kit dentro de `.ai/`, exceto caminhos fixos das ferramentas | Uma pasta só para instalar, remover e fazer backup |
| 7 | ADR do agente nasce `proposed`; vira `accepted` só por você (`aikit adr accept` ou merge do PR) | Evita registrar decisão de agente como decisão do projeto |
| 8 | Máximo 5 personas; o dev é a thread principal do Claude, não um subagent | Persona demais polui a auto-delegação e custa tokens |
| 9 | Personas base vivem no kit; o projeto guarda só overrides | `git pull` no kit + `aikit build` atualiza todos os projetos; releases com tag e versão gravada em .ai/ para o doctor apontar deriva |
| 10 | CLI em Python 3.11+ (PyYAML, jsonschema), instalado com `uv tool install -e` | Simples, testável, sem servidor |
| 11 | Runbooks em `docs/runbooks/`, versionados como os ADRs | Runbook serve ao time às 3 da manhã; privado não cumpre esse papel |
| 12 | Tipo Diátaxis inferido da pasta em `docs/`; frontmatter `type:` só para exceção e para `.ai/docs/` | Menos frontmatter para manter; o índice agrupa igual e cada persona lê só o tipo que importa |
| 13 | `init` cria só `docs/decisions/` e `docs/runbooks/`; `architecture/`, `reference/` e `guides/` nascem com o primeiro doc | Pasta vazia versionada é ruído no PR e parece documentação abandonada |

## Estrutura do repo ai-kit

Um repo, clonado em `~/ai-kit`, com o CLI instalado via `uv tool install -e ~/ai-kit` (modo editável: `git pull` no clone já atualiza o CLI).

```
ai-kit/
  README.md
  pyproject.toml
  aikit/                  # pacote Python do CLI
    cli.py                # init, build, lint, adr, runbook, backup, doctor, uninstall, hook
    core.py               # paths, YAML, frontmatter, escrita idempotente
    compile_personas.py   # YAML -> .claude/agents/*.md + bloco de gates do AGENTS.md
    merge.py              # base + overlay + override do projeto
    build.py              # plano de escrita (o doctor reusa para detectar build atrasado)
    index_builder.py      # gera .ai/index.yaml
    records.py            # ciclo de vida de ADRs e runbooks
    lint.py               # schemas, integridade de ADR, Diátaxis, orçamentos, --refs
    install.py            # init/uninstall, manifesto, merge do settings.local.json
    exclude.py            # bloco delimitado em .git/info/exclude
    backup.py, doctor.py, hook.py
  personas/               # base: architect, reviewer, security, qa, tech-writer
  overlays/
    _example/             # mostra como adicionar regras de domínio
  schemas/                # JSON Schema: persona, project, adr-frontmatter, index
  templates/              # AGENTS.md, CLAUDE.md, project.yaml, adr.md
  skills/                 # aikit-onboard, aikit-adr, aikit-docs-sync (SKILL.md)
  hooks/                  # config do hook PostToolUse
  docs/decisions/         # ADRs do próprio kit
  tests/                  # pytest + fixtures de projetos fake
```

## O que o kit instala num projeto

A mecânica do kit fica fora do git, listada num bloco `# >>> ai-kit` em `.git/info/exclude` que o `aikit uninstall` remove. `docs/` é versionado: é o conhecimento do projeto, do time. As pastas `docs/architecture/`, `docs/reference/` e `docs/guides/` não existem no init — nascem quando o agente ou você escreve o primeiro doc do tipo.

| Caminho | Git | Origem | Conteúdo |
| --- | --- | --- | --- |
| `docs/decisions/ADR-*.md` | sim | escrito por agente ou humano | ADRs do projeto |
| `docs/runbooks/*.md` | sim | aikit runbook new + agente ou você | Procedimentos operacionais (how-to): deploy, rollback, incidente |
| `docs/{architecture,reference,guides}/` | sim | sob demanda, com o primeiro doc | Explanation, reference e tutorial |
| `.ai/AGENTS.md` | não | template + onboard | Instruções reais, até 60 linhas |
| `.ai/project.yaml` | não | skill `aikit-onboard` | Stack, comandos, convenções, paths |
| `.ai/index.yaml` | não | gerado pelo build | Mapa de personas, ADRs e docs |
| `.ai/personas/*.yaml` | não | escrito por você | Só overrides do projeto (opcional) |
| `.ai/overlays.yaml` | não | escrito por você | Overlays ativos, ex. `[lgpd]` |
| `.ai/docs/*.md` | não | agente / você | Notas longas privadas |
| `CLAUDE.md` | não | template | Uma linha: `@.ai/AGENTS.md` |
| `AGENTS.md` | não | symlink | Aponta para `.ai/AGENTS.md` (Codex, Cursor) |
| `.claude/agents/aikit-*.md` | não | gerado pelo build | Subagents com cabeçalho "não editar" |
| `.claude/skills/aikit-*` | não | copiado do kit | Os 3 skills |
| `.claude/settings.local.json` | não | merge pelo init e pelo build | Hooks PostToolUse (build) e PreToolUse (bloqueio de commit na branch padrão) |
| `.ai/wishes/*.md` | não | `aikit wish new` + agente | Wishes; só `draft` e `approved` entram no índice |

**Conflito com arquivos do time**: se o projeto já tiver `CLAUDE.md` ou `AGENTS.md` versionados, o `init` não toca neles e avisa. Nesse caso o import do `.ai/AGENTS.md` vai por um caminho privado (ver Riscos).

## Contrato de contexto

O que entra em cada sessão, e quanto custa. É o critério objetivo do `lint`.

**Sempre carregado** (custo fixo por sessão):

- `CLAUDE.md` → `.ai/AGENTS.md` (≤ 60 linhas)
- `description` dos 5 subagents (para auto-delegação)
- `description` dos 3 skills

**Sob demanda** (só quando a tarefa pede):

- `.ai/index.yaml` (≤ ~2k tokens) — a porta de entrada; aberto pelo agente quando precisa de contexto
- ADRs, runbooks e docs — abertos individualmente a partir do índice, nunca varridos

O `lint` orça os dois blocos: avisa se o sempre-carregado (AGENTS.md + descriptions) ou o índice estourarem o limite, e se uma persona compilada passar de ~40 linhas (listas `principles`/`never` são aditivas no merge e só crescem).

## Formatos

Todos validados por JSON Schema no `aikit lint`.

**Persona (`personas/architect.yaml`)**

```yaml
id: architect
model: opus                 # opus | sonnet | haiku
tools: [Read, Grep, Glob, Write]
description: >              # vira o description do subagent (auto-delegação)
  Use para decisões de arquitetura, tradeoffs e para escrever ADRs.
role: Decide arquitetura com tradeoffs explícitos
gates: [plan, adr]          # plan | adr | ship (ship = chamada pelo /aikit-ship)
reads: [project, decisions, explanation]   # seções e tipos Diátaxis do index que ela consulta
principles:
  - Escolha a opção mais simples que atende os requisitos de hoje
  - Toda decisão não trivial vira ADR com status proposed
never:
  - Implementar código
  - Decidir sem listar ao menos 2 alternativas
outputs:
  adr: "{paths.adr}/ADR-{n:04d}-{slug}.md"
```

Merge: base do kit, depois overlays na ordem de `overlays.yaml`, depois override do projeto. Listas (`principles`, `never`, `tools`) somam; escalares (`model`, `role`) substituem.

O `reads` não é só metadado: o compilador o traduz em instrução explícita no `.md` gerado ("consulte apenas as seções X do `index.yaml`; não abra docs de outros tipos"). Sem isso cada subagent relê tudo num contexto novo e o ganho do índice se perde justamente onde mais custa.

**Projeto (`.ai/project.yaml`)**

```yaml
name: meu-servico
stack: [python-3.12, fastapi, postgres]
commands:
  test: pytest -q
  lint: ruff check .
  run: uvicorn app.main:app --reload
conventions:
  - Type hints obrigatórios
  - Migrações via alembic
paths:
  src: app/
  tests: tests/
  adr: docs/decisions/     # padrão; configurável se o projeto já tiver outra convenção
  runbooks: docs/runbooks/
docs_max_age_days: 90      # runbook sem verificação há mais que isso gera aviso
```

**ADR (`docs/decisions/ADR-0003-drizzle.md`)**

```markdown
---
id: ADR-0003
title: Trocar Prisma por Drizzle
status: proposed      # proposed | accepted | rejected | superseded
date: 2026-10-08
supersedes: ADR-0001
superseded_by: null
body_sha: null        # gravado pelo aikit adr accept
tags: [db, orm]
summary: Drizzle no lugar de Prisma por SQL explícito e bundle menor
---
## Contexto
## Opções
## Decisão
## Consequências
```

Regra: corpo imutável depois de `accepted`. A única mutação permitida é `status` e `superseded_by` quando um ADR novo substitui. O lint confere o corpo contra o body_sha, o que funciona com ou sem git.

**Runbook (`docs/runbooks/rollback-deploy.md`)**

```markdown
---
id: RB-rollback-deploy
title: Reverter deploy com falha
trigger: Erro 5xx acima do normal logo após um deploy
last_verified: 2026-10-08
tags: [deploy, incidente]
summary: Volta para a versão anterior e confirma saúde do serviço
---
## Quando usar
## Pré-requisitos
## Passos
## Verificação
## Se não resolver (escalonamento)
```

**Tipo Diátaxis vem da pasta**: `decisions/` e `architecture/` = explanation, `runbooks/` = how-to, `reference/` = reference, `guides/` = tutorial. Frontmatter `type:` só para exceção e para `.ai/docs/` (notas privadas, sem pasta tipada — sem `type:` o `lint` rejeita). O `lint` acusa `type:` inconsistente com a pasta e runbook com `last_verified` mais velho que `docs_max_age_days`.

**Índice (`.ai/index.yaml`, gerado)**

```yaml
generated: 2026-10-08        # só data; hora completa muda a cada build e gera diff sem valor
project: .ai/project.yaml
personas: [architect, reviewer, security, qa, tech-writer]
wishes:  # approved = em andamento (retome por ele); draft = aguarda aprovação humana
  - {path: .ai/wishes/migrar-auth-para-jwt.md, status: approved, summary: JWT com refresh}
decisions_dir: docs/decisions  # arquivo: <id>-*.md (path fora das entradas: -34% de tamanho)
decisions:
  - {id: ADR-0003, status: proposed, tags: [db, orm], summary: Drizzle no lugar de Prisma}
  - {id: ADR-0001, status: superseded}   # superseded/rejected viram uma linha; o frontmatter completo segue no arquivo
docs:                 # agrupado por tipo Diátaxis (inferido da pasta)
  explanation:
    - {path: docs/architecture/overview.md, summary: Módulos e fluxo de dados}
  how-to:
    - {id: RB-rollback-deploy, path: docs/runbooks/rollback-deploy.md, tags: [deploy, incidente], last_verified: 2026-10-08, summary: Reverter deploy com falha}
```

Dieta do índice, para caber nos ~2k tokens conforme o projeto cresce: `summary` com no máximo 80 caracteres (o `lint` rejeita acima disso), ADRs `superseded`/`rejected` reduzidos a `{id, status}`, ADRs sem `path` (vem de `decisions_dir`), grupos vazios omitidos e `generated` só com a data, que só muda quando o conteúdo muda. Medido: 17 ADRs custam ~510 tokens. Orçamentos completos na seção Contrato de contexto.

## CLI, skills e hooks

Divisão de trabalho: o CLI faz o mecânico e determinístico; os skills fazem o que exige ler e entender o código.

**CLI `aikit`**

| Comando | O que faz |
| --- | --- |
| `aikit init [--overlay x]` | Cria `.ai/`, `docs/decisions/`, `docs/runbooks/`, copia skills, mescla hook, escreve bloco no exclude, grava manifesto dos arquivos criados em .ai/manifest.json, roda build; termina imprimindo o próximo passo ("abra o Claude Code e rode /aikit-onboard") |
| `aikit build` | Mescla personas, gera `.claude/agents/*.md`, regenera `index.yaml` |
| `aikit lint` | Valida YAMLs e frontmatters contra schemas, checa os orçamentos do Contrato de contexto |
| `aikit adr new "título"` | Próximo número, arquivo do template, `status: proposed` |
| `aikit adr supersede 0001 0003` | Marca o antigo como superseded e liga os dois |
| `aikit adr accept 0003` | Muda para accepted e grava body_sha; só você roda (localmente ou no branch do PR antes do merge) |
| `aikit adr reject 0003` | Marca um ADR `proposed` como rejected |
| `aikit runbook new "título"` | Cria runbook do template em paths.runbooks com last_verified de hoje |
| `aikit runbook verify <slug>` | Marca o runbook como verificado hoje |
| `aikit wish new "título"` | Cria wish `draft` em `.ai/wishes/` (resumo, escopo, decisões, critérios de aceite, passos, próxima sessão) |
| `aikit wish approve <slug>` | Só humano: exige critérios preenchidos, marca `approved`, cria a branch `wish/<slug>` e troca para ela; com `git.worktrees: true`, abre-a no worktree `wt-<iniciais>-<slug>` (ADR-0023) |
| `aikit wish done <slug>` | Conclui o wish `approved` (sai do índice) e avisa critérios não marcados; com worktree, oferece removê-lo se estiver limpo |
| `aikit lint --refs` | Também acusa paths citados em docs que não existem (a parte mecânica do docs-sync) |
| `aikit hook post-edit` / `pre-bash` | Entradas dos hooks PostToolUse e PreToolUse (leem o JSON do stdin) |
| `aikit backup` | Copia `.ai/` (project.yaml, overrides, notas privadas) para um repo privado seu, uma pasta por projeto; ADRs e runbooks já viajam no git do projeto |
| `aikit doctor` | Checa exclude, links, build em dia, versão do kit vs projeto, idade do último backup |
| `aikit uninstall` | Remove só o que está no manifesto, tira só a entrada do hook do settings.local.json e limpa o exclude; `docs/` inteiro fica — é do time |

Todo comando que muta estado (`adr`, `runbook`, `plan`) roda `build` implicitamente ao final — o build é rápido e idempotente. Assim o índice nunca fica desatualizado nem quando você edita fora do Claude Code; o hook vira redundância para edições do agente, não a única garantia.

**Skills (copiados para `.claude/skills/`)**

Todos com prefixo `aikit-`, pela mesma razão dos subagents: skill sem prefixo pode colidir com skill do usuário ou do time. `aikit-onboard`, `aikit-ship` e `aikit-docs-sync` são acionados por você (`/nome`) e usam `disable-model-invocation: true`, o que tira a description deles do contexto fixo; só `aikit-adr` e `aikit-wish` ficam disponíveis para o modelo, e as descriptions deles fazem o roteamento.

- `aikit-onboard`: lê o repo, preenche `project.yaml` e o `AGENTS.md`, roda `aikit build`. Roda uma vez por projeto.
- `aikit-adr`: chama `aikit adr new` e escreve Contexto, Opções, Decisão, Consequências. Termina imprimindo o comando pronto (`aikit adr accept NNNN`) para você rodar, já que só você aceita.
- `aikit-wish`: cria o wish em `draft` e para pedindo aprovação; depois de aprovado, retoma por ele e atualiza "Próxima sessão" antes de encerrar.
- `aikit-ship`: gate antes do PR. Roda teste e lint, chama as personas de gate `ship` em paralelo (security só se o diff for sensível), lista ADRs `proposed` pendentes e devolve PODE ABRIR PR, CORRIGIR ou BLOQUEADO.
- `aikit-docs-sync`: o tech-writer compara `.ai/docs/`, ADRs e runbooks com o código (comandos e paths citados ainda existem?) e propõe correções, sem aplicar sozinho.

**Regra de decisão (no bloco gerado do `AGENTS.md`)**: cabe numa sessão e não restringe o futuro → só faça; escolha cara de desfazer → ADR; várias sessões → wish; na dúvida, pergunte. Não há gateway que classifica cada pedido: custaria em todo pedido para acertar a minoria. A checagem "decisão estrutural sem ADR" acontece uma vez por PR, no reviewer, sobre o diff real. As regras do kit ficam no bloco gerado para que `aikit build` as atualize em todos os projetos.

**Hook (`.claude/settings.local.json`)**

- `PostToolUse` em `Edit|Write` roda `aikit hook post-edit`, que lê `tool_input.file_path` do stdin e só faz build se o caminho estiver em `.ai/**` ou `docs/**`.
- `PreToolUse` em `Bash` roda `aikit hook pre-bash`: se há um commit em posição de comando e o repo está na branch padrão, sai com código 2 e o Claude recebe a instrução de criar a branch (ADR-0019).
- O mesmo hook bloqueia `aikit adr accept` e `aikit wish approve` quando quem roda é o agente (ADR-0020). Você roda no terminal ou com `!` no Claude Code.
- Se o build achar problema (ex.: override inválido), o hook sai com código 2 e a mensagem volta para o Claude corrigir. O comando é gravado com caminho absoluto do `aikit`, porque o shell do hook pode não ter o mesmo PATH.

## Sem Genie (ADR-0018)

A integração com o Genie foi removida em 8 Out 2026. Instalado, ele somava 18 skills globais ao contexto de toda sessão, e três se sobrepunham às personas. As duas coisas que ele dava e que faziam falta foram cobertas com peças pequenas: wishes com aprovação humana (escopo e estado entre sessões; ADR-0020) e `/aikit-ship` (gate de revisão que não depende de lembrar). O que fica de fora é a execução autônoma e paralela de tarefas longas.

## Fases

Sete fases curtas, cada uma fecha com um teste que dá para rodar.

1. **Esqueleto e ADRs do kit**
   - Repo, `pyproject.toml`, `uv tool install -e`, `aikit --help` funcionando
   - Schema de adr-frontmatter (adiantado da fase 2) e 17 ADRs em `docs/decisions/`: as 12 decisões originais, a 13 nova, e 4 que substituem as originais 4, 5, 11 e 12
   - Pronto quando: `aikit --version` roda e os ADRs passam no schema
2. **Schemas e compilador de personas**
   - JSON Schemas de persona, project e index (adr-frontmatter já vem da fase 1)
   - `compile_personas.py` e `merge.py` (base, overlay, override)
   - Pronto quando: pytest cobre merge de listas e escalares e o `.md` gerado tem frontmatter válido para o Claude Code
3. **`init`, `uninstall`, `doctor` e exclude**
   - Bloco delimitado em `.git/info/exclude`, idempotente
   - Detecta `CLAUDE.md`/`AGENTS.md` versionados e não sobrescreve
   - `aikit backup` (adiantado da v2): sem ele, um clone novo perde o `.ai/` (project.yaml, overrides, notas)
   - Pronto quando: init + uninstall num repo fixture deixam o `git status` limpo fora de `docs/`; `docs/decisions/` e `docs/runbooks/` criados no init permanecem após o uninstall
4. **ADRs e índice**
   - `adr new`, `adr supersede`, `adr accept` (grava `body_sha`), `index_builder.py` lendo frontmatters, personas, `.ai/docs` e `.ai/wishes`
   - `runbook new`, tipo Diátaxis inferido da pasta (frontmatter só para exceção e `.ai/docs/`), índice agrupado por tipo, aviso de `last_verified` vencido
   - Pronto quando: superseder um ADR atualiza os dois arquivos e o índice; `lint` acusa ADR `accepted` sem `body_sha` ou com corpo que não bate com ele
5. **Conteúdo das 5 personas e templates**
   - architect, reviewer, security, qa, tech-writer; `AGENTS.md` e `CLAUDE.md` templates
   - Use BMAD (voz e handoff) e wshobson/agents (formato e model tiering) como referência, reescrevendo
   - Pronto quando: cada persona é invocada pelo nome no Claude Code e respeita `never` num teste manual roteirizado
6. **Skills e hook**
   - `aikit-onboard`, `aikit-adr`, `aikit-docs-sync`; hook PostToolUse
   - Pronto quando: editar uma persona override pelo Claude dispara o build sozinho
7. **Piloto em 2 repos reais e overlay**
   - Um repo Python, um Next.js
   - Overlay `_example` documentado
   - Pronto quando: 3 tarefas reais entregues com `/aikit-ship` antes do PR, pelo menos 1 wish aprovado e retomado em sessão nova e 1 ADR aceito via PR

## Riscos e pontos a verificar

Verificados na documentação do Claude Code em 8 Out 2026 (code.claude.com/docs: memory, sub-agents, skills, hooks).

- [x] **Import privado quando o time já tem `CLAUDE.md`**: `CLAUDE.local.md` não está deprecado e é lido junto do `CLAUDE.md`. O `init` grava o import nele (testado)
- [x] **Colisão de nomes de subagent**: resolvido, os gerados sempre levam prefixo, então um `reviewer.md` do time não colide com o gerado (`aikit-reviewer`)
- [x] **Merge do hook**: o `init` mescla o JSON e o `uninstall` tira só a entrada do kit, preservando o resto (testado)
- [x] **Caminhos fixos do Genie**: superado pelo ADR-0018 (integração removida). Registro: o `genie init` versiona `.genie/` e ignora o próprio `genie.db` no `.gitignore` do projeto
- [x] **Recarga de subagents na sessão**: o Claude Code relê `.claude/agents/` alterados sem reiniciar; a exceção é o primeiro arquivo num diretório `agents/` que não existia quando a sessão abriu (aí vale na próxima sessão). Hook testado ao vivo: editar um override pelo Claude recompilou o subagent
- [x] **AGENTS.md nativo**: o Claude Code lê `AGENTS.md` só quando não há `CLAUDE.md`; como o kit cria `CLAUDE.md` com o import, o symlink serve a Codex e Cursor

Riscos de uso:

- **Clone novo perde o privado**: o `.ai/` não viaja com o repo (ADRs e runbooks agora viajam, em `docs/`). Sobram project.yaml, overrides e notas. Mitigação já na v1 (fase 3): `aikit backup` para um repo privado seu, por projeto. Backup manual vai ser esquecido: o `doctor` avisa quando o último passar de 7 dias; auto-commit no build fica para v2
- **Setup visível nos PRs do cliente**: ADRs `proposed` escritos por agente aparecem no git antes de você aceitar. Custo aceito na decisão 4; se incomodar num projeto, aceite ou descarte antes do push
- **Custo de tokens**: cada revisor a mais soma. Medir no piloto quantas vezes cada persona do `/aikit-ship` muda o veredito, e cortar a que não muda
- **Deriva do kit**: projetos com versão velha do kit. O `doctor` compara versão gravada em `.ai/` com a do kit
