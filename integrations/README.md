# Automações de integração

Esta pasta contém a implementação e os testes da distribuição de skills, commands
e agentes aos consumidores (hoje, o Cursor). Os arquivos declarativos ficam em
[`config/`](../config/README.md), organizados por consumidor.

- `scripts/agents_config.py`: CLI de gerenciamento das conexões (`plan`, `connect`, `sync`, `status`, `doctor`, `disconnect`, `validate`).
- `scripts/hub_bootstrap.py`: descoberta das configurações e resolução dos destinos (também instala sozinho, sem recibo).
- `scripts/validate_hub_manifest.py`: validação dos `integration.json`, das skills, dos agentes e dos locks.
- `tests/`: testes de conexão, sincronização, validação e remoção. Usam diretórios temporários, nunca o `HOME` real.

Use o `Makefile` da raiz ou chame a CLI diretamente:

```bash
python3 integrations/scripts/agents_config.py validate
python3 integrations/scripts/agents_config.py plan cursor
python3 integrations/scripts/agents_config.py connect cursor
python3 integrations/scripts/agents_config.py sync cursor
```

A CLI só cria symlinks que ela mesma registra num recibo local, em
`~/.agents-config/receipts/<consumidor>.json`. Nada existente é sobrescrito, e
`sync` e `disconnect` só removem links que ainda apontam para onde o recibo diz.

Variáveis de ambiente:

- `AGENTS_CONFIG_INSTALL_HOME`: substitui o `HOME` como base de instalação e dos recibos (útil para testar com um diretório temporário).
- `AGENTS_CONFIG_CURSOR_HOME`: substitui o diretório do Cursor (padrão `~/.cursor`). Cada consumidor declara a sua em `home.home_env`.

Para ensaiar sem tocar na máquina:

```bash
AGENTS_CONFIG_INSTALL_HOME=$(mktemp -d) make connect-cursor
```
