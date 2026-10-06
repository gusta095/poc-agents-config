# AGENTS.md

Regras deste repositório.

## O que é

Hub que versiona skills e agentes e os conecta a consumidores (hoje, o Cursor) por symlink, guiado por `config/<nome>/integration.json`. Visão geral em [`README.md`](./README.md); contrato dos adaptadores em [`config/README.md`](./config/README.md).

## Estrutura

- `skills/<nome>/`: fonte única das skills (têm `SKILL.md`); proveniência em `skills/skills.lock.json`.
- `agents/<nome>.md`: agentes, opcionais; proveniência em `agents/agents.lock.json`. A pasta só existe quando houver agentes.
- `config/<nome>/`: o adaptador de um consumidor, com o `integration.json`. Adicionar um consumidor é criar essa pasta.
- `integrations/scripts/`: CLI (`agents_config.py`), validação e bootstrap. `integrations/tests/`: testes deles.
- `scripts/ci/` e `tests/`: descoberta das suítes de skills e seus testes.

## Comandos

O `Makefile` é a interface: `make help` lista tudo. `make check` roda `validate` e todos os testes; `make plan-<nome>`, `connect-<nome>`, `sync-<nome>`, `disconnect-<nome>`, `status` e `doctor` operam a conexão. Sem `make`: `python3 integrations/scripts/agents_config.py <comando>`.

Rode `make check` antes de concluir qualquer mudança em `config/`, `integrations/`, `skills/` ou `agents/`.

## Regras

- `skills/` é a fonte única das skills. Não duplique skills dentro de `config/`.
- O nome da pasta da skill, o campo `name:` do `SKILL.md` e a chave em `skills/skills.lock.json` devem ser idênticos. O mesmo vale para agentes: arquivo, `name:` e chave em `agents/agents.lock.json`. A origem (`own` ou `upstream`) vem só do lock, nunca do nome.
- Toda skill e todo agente têm entrada no lock, com `origin`; para `upstream`, também `repo`, `path`, `ref`, `fetched`, `license`, `local_changes` e `notes` (`null` no que não se sabe, sem inventar).
- Uma skill, comando ou agente só chega ao consumidor se estiver em `names` do `integration.json`. Use `disabled` para o que fica de fora de propósito.
- Não altere a estrutura do repositório (diretórios, formato do `integration.json`, contrato dos adaptadores) sem pedido explícito.
- Nunca sobrescreva um destino que o hub não criou. `connect`, `sync` e `disconnect` só tocam o que está no recibo local.
- Sem wrappers escritos à mão por consumidor: o `Makefile` só chama a CLI e descobre os consumidores pelas pastas.
- Testes e experimentos de conexão usam `AGENTS_CONFIG_INSTALL_HOME` com um diretório temporário; `~/.cursor` é a instalação real do usuário.
- Não versione estado local (recibos, caches, arquivos de editor, credenciais, saídas temporárias).
- Todo conteúdo deve ser genérico: sem nomes pessoais, caminhos absolutos ou e-mails.

## Commits

Use commits convencionais (`feat:`, `fix:`, `docs:`, `chore:`...). Não commite sem o usuário pedir.
