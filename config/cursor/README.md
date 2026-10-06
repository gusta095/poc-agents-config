# Adaptador Cursor

Configuração para usar as skills deste repositório no Cursor, em Linux/Ubuntu (WSL conta como Linux). O caminho principal é conectar pelo hub (`make connect-cursor`); a cópia manual com `cp` é a alternativa.

## Conteúdo

| Arquivo | Função |
| --- | --- |
| `integration.json` | Declara o que o hub liga ao Cursor e o que fica desabilitado. |
| `AGENTS.md` | Template de entrada do projeto; aponta para as skills. |
| `.cursor/rules/commit-messages.mdc` | Rule sempre ativa: antes de `git commit`, seguir a skill `caveman-commit`. |
| `.cursor/rules/planning.mdc` | Rule acionada por contexto (`alwaysApply: false`): planejamento via skill `planning`. |
| `.cursor/commands/commit.md` | Comando `/commit`. |
| `.cursor/commands/plan.md` | Comando `/plan`. |

As skills não ficam aqui: a fonte única é `skills/` na raiz do repositório.

## Caminho principal: conectar pelo hub

Requisitos: `python3` e `make`. Na raiz do repositório:

```bash
make plan-cursor      # mostra o que seria ligado, sem alterar nada
make connect-cursor   # cria os symlinks
make status           # confirma a conexão
make doctor           # checagens de ambiente
```

O que o `connect` faz, conforme o `integration.json`:

| Item | Estado | Resultado |
| --- | --- | --- |
| skills `caveman-commit`, `planning` | habilitadas | `~/.cursor/skills/<nome>` aponta para `skills/<nome>` |
| commands `commit`, `plan` | habilitados | `~/.cursor/commands/<nome>.md` aponta para `config/cursor/.cursor/commands/<nome>.md` |
| agents | nenhum habilitado | nada é ligado (`agents.names` vazio; o hub não traz agentes) |
| arquivo global de regras (`entry`) | não existe | o Cursor não tem arquivo global de regras em disco |
| rules do projeto | fora do `connect` | copiadas para o projeto (abaixo) |

As listas `disabled` do `integration.json` guardam o que existe no hub e foi deixado de fora de propósito (hoje vazias). Para habilitar ou desabilitar um item, mova o nome entre `names` e `disabled`, valide e sincronize:

```bash
make validate
make sync-cursor
```

O `sync` remove só o link que o hub criou; um destino que você alterou à mão nunca é apagado. Para desfazer tudo: `make disconnect-cursor`.

### Rules do projeto

As rules são por projeto e continuam sendo copiadas:

```bash
DEST=/caminho/do/projeto
mkdir -p "$DEST"/.cursor && cp -r config/cursor/.cursor/rules "$DEST"/.cursor/
cp config/cursor/AGENTS.md "$DEST"/
```

Se o projeto já tem `AGENTS.md` ou `.cursor/rules/`, mescle manualmente em vez de sobrescrever.

### Ensaiar sem tocar no ~/.cursor

```bash
AGENTS_CONFIG_INSTALL_HOME=$(mktemp -d) make connect-cursor
```

Para usar outro diretório do Cursor, defina `AGENTS_CONFIG_CURSOR_HOME`.

## Alternativa manual (cp)

Sem o hub, copie tudo para o projeto de destino. Não acompanha mudanças do hub:

```bash
DEST=/caminho/do/projeto

cp -r config/cursor/.cursor "$DEST"/
cp config/cursor/AGENTS.md "$DEST"/
mkdir -p "$DEST"/.cursor/skills
cp -r skills/*/ "$DEST"/.cursor/skills/
```

Se o projeto já tem `AGENTS.md` ou `.cursor/`, mescle manualmente.

## Validação

1. Abra uma sessão nova no Cursor.
2. Em Settings > Rules, confirme que as rules do projeto aparecem.
3. Digite `/commit` e `/plan` e confirme que os comandos existem.
4. Confirme que as skills `caveman-commit` e `planning` aparecem como skills do Cursor.

## Compatibilidade

O formato exato de skills, commands e agentes do Cursor não foi confirmado em documentação durante a criação deste adaptador. Em especial, não foi verificado:

- se a sua versão do Cursor descobre skills em `~/.cursor/skills` e commands em `~/.cursor/commands` (e agentes em `~/.cursor/agents`);
- se o Cursor segue symlinks nesses diretórios.

Por isso as rules e os commands apontam diretamente para o caminho do `SKILL.md` (em `~/.cursor/skills` ou, na cópia manual, `.cursor/skills`): assim o fluxo funciona como fallback mesmo sem suporte nativo a skills. Se o Cursor não seguir symlinks ou usar outro caminho, use a alternativa manual com `cp` ou ajuste `skills.target_subdir`, `commands.target_subdir` e `agents.target_subdir` no `integration.json` e rode `make sync-cursor`.
