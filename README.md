# poc-agents-config

Hub que versiona skills (e, opcionalmente, agentes) para agentes de código e as conecta a um consumidor, com testes e validação. O consumidor suportado hoje é o Cursor, em Linux/Ubuntu (WSL conta como Linux).

A fonte única fica neste repositório; `make connect-cursor` liga o que está habilitado ao `~/.cursor` por symlinks. Editar uma skill aqui vale na hora, sem copiar de novo.

## Estrutura

```
.
├── AGENTS.md                      # regras deste repositório
├── Makefile                       # interface de comandos (chama a CLI)
├── skills/                        # fonte única das skills
│   ├── skills.lock.json           # proveniência de cada skill
│   ├── caveman-commit/            # mensagens de commit curtas (Conventional Commits)
│   └── planning/                  # planejamento executável antes de implementar
├── agents/                        # opcional: agentes (não existe por padrão)
├── config/
│   ├── README.md                  # contrato dos adaptadores
│   ├── template/README.md         # como criar um adaptador novo
│   └── cursor/                    # adaptador Cursor
│       ├── integration.json       # o que é conectado e o que está desabilitado
│       ├── AGENTS.md              # template de entrada para o projeto
│       └── .cursor/               # rules e commands
├── integrations/
│   ├── scripts/                   # CLI (agents_config.py), validação e bootstrap
│   └── tests/                     # testes da CLI, do manifesto e do bootstrap
├── scripts/ci/                    # descoberta das suítes de teste das skills
└── tests/                         # testes dos scripts da raiz
```

## Skills incluídas

- `caveman-commit`: escreve a mensagem de commit comprimida à intenção, no formato Conventional Commits.
- `planning`: produz specs e um plano executável, proporcional ao problema, antes da implementação.

## Uso no Ubuntu

Requisitos: `python3` (3.10 ou superior) e `make`.

```bash
make help              # lista os alvos
make validate          # valida integration.json, skills e locks
make plan-cursor       # mostra o que seria ligado, sem alterar nada
make connect-cursor    # liga skills e commands em ~/.cursor
make status            # estado da conexão
make doctor            # status mais checagens de ambiente
make sync-cursor       # refaz os links após mudar o integration.json
make disconnect-cursor # remove os links criados pelo hub
make check             # validate e todos os testes
```

O `connect` nunca sobrescreve um destino que o hub não criou: se `~/.cursor/skills/planning` já existir, ele para e avisa. Os links criados ficam registrados num recibo local em `~/.agents-config/receipts/cursor.json` (não versionado). Para ensaiar sem tocar no `~/.cursor`:

```bash
AGENTS_CONFIG_INSTALL_HOME=$(mktemp -d) make connect-cursor
```

Sem `make`, chame a CLI: `python3 integrations/scripts/agents_config.py <comando> [consumidor]`.

## integration.json

`config/cursor/integration.json` declara o que o hub liga ao Cursor. Cada bloco tem `names` (habilitados) e `disabled` (existem no hub e ficam de fora de propósito):

| Bloco | O que liga | Destino |
| --- | --- | --- |
| `skills` | `caveman-commit`, `planning` | `~/.cursor/skills/<nome>` |
| `commands` | `commit`, `plan` | `~/.cursor/commands/<nome>.md` |
| `agents` | nenhum (lista vazia) | `~/.cursor/agents/<nome>.md` |

O Cursor não tem arquivo global de regras em disco, por isso não há bloco `entry`. As rules do projeto continuam em `config/cursor/.cursor/rules/` e são copiadas para o projeto. Para desligar um item, mova-o de `names` para `disabled` e rode `make sync-cursor`. O contrato completo está em [config/README.md](config/README.md).

## Agentes

O hub suporta agentes, mas não traz nenhum. Para adicionar um:

1. Crie `agents/<nome>.md` com frontmatter `name:` (igual ao nome do arquivo) e `description:`, e o prompt no corpo.
2. Crie `agents/agents.lock.json` (ou acrescente a entrada):

   ```json
   { "schema_version": 1, "agents": { "<nome>": { "origin": "own" } } }
   ```

3. Liste o agente em `agents.names` de `config/cursor/integration.json`.
4. Rode `make validate` e `make sync-cursor`.

O formato exato de agentes que o Cursor lê não foi confirmado (ver Compatibilidade).

## Alternativa manual (sem make)

Para copiar a configuração para um projeto sem usar o hub, siga o passo a passo com `cp` em [config/cursor/README.md](config/cursor/README.md#alternativa-manual-cp). Cópias não acompanham mudanças do hub.

## Adicionando uma skill

1. Crie `skills/<nome>/SKILL.md` com `name:` igual ao nome da pasta.
2. Registre a skill em `skills/skills.lock.json`.
3. Acrescente-a a `skills.names` de `config/cursor/integration.json`.
4. Rode `make check` e `make sync-cursor`.

## Compatibilidade

O formato de skills, commands e agentes do Cursor não foi confirmado em documentação durante a criação deste hub. Detalhes e fallback em [config/cursor/README.md](config/cursor/README.md#compatibilidade).
