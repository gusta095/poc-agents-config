# Contrato de adaptadores

Este documento define o que todo adaptador de consumidor (hoje, o Cursor)
precisa declarar e o que a conexão garante. Não há manifesto central: cada
adaptador declara a si mesmo em `config/<nome>/integration.json`, e nenhum
destino de instalação deve ficar codificado apenas dentro de um script.

## O que um adaptador é

Um diretório em `config/<nome>/` com o `integration.json`, que declara como
conectar o consumidor, e os arquivos que ele distribui (por exemplo, os
commands do Cursor). O diretório é autocontido: adicionar um consumidor é
criar essa pasta, sem editar nenhum arquivo central.

O arquivo de entrada global (`entry`) é **opcional**. Consumidores que
têm um arquivo global de regras em disco (um `AGENTS.md` em `$HOME`, por
exemplo) o declaram em `entry`; o Cursor não tem, então o adaptador dele só liga
skills, commands e agentes. Quando existe, o arquivo de entrada deve ser mínimo:
aponta para as skills e, se preciso, manda acionar uma skill que não pode deixar
de rodar. Nada além disso: duplicar conteúdo canônico aqui é a forma mais comum
de o adaptador divergir da fonte da verdade sem ninguém perceber.

## O que vai no `integration.json`

O arquivo fica em `config/<nome>/integration.json` e tem:

- `schema_version`: hoje `1`.
- `name`: igual ao nome do diretório (o validador falha se divergir).
- `home` (obrigatório se não houver `entry`): onde fica o diretório do consumidor.
  - `home.home_env`: lista ordenada de variáveis de ambiente que, se definidas,
    sobrescrevem esse diretório (a primeira definida vence).
  - `home.home_default`: subdiretório padrão dentro do `HOME` do usuário (ex.: `.cursor`).
- `entry` (opcional): arquivo de entrada global do consumidor.
  - `entry.source`: caminho do arquivo, relativo ao diretório do adaptador.
  - `entry.target_name`: nome do link dentro do diretório home do consumidor.
  - `entry.home_env` e `entry.home_default`: só quando não há bloco `home`
    (mesmo significado de `home.*`). Com `home`, o `entry` não os repete.
- `skills`:
  - `skills.base`: `"entry_home"` (skills dentro do diretório do consumidor, como
    `~/.cursor/skills`) ou `"install_home"` (relativo ao `HOME`, para um diretório
    compartilhado). O nome `entry_home` é histórico: vale para o bloco `home` também.
  - `skills.target_subdir`: subdiretório de skills relativo à base escolhida.
  - `skills.names`: skills **habilitadas**, as que o `connect` liga.
  - `skills.disabled` (opcional): skills **desabilitadas de propósito**. Documenta
    o que existe no hub e este consumidor não usa.
- `commands` (opcional): prompts reutilizáveis, um arquivo por comando.
  - `commands.source_dir`: pasta dos arquivos, relativa ao diretório do adaptador
    (ex.: `.cursor/commands`).
  - `commands.target_subdir`: pasta de destino dentro do home do consumidor.
  - `commands.suffix` (opcional, padrão `.md`) e `commands.names`/`commands.disabled`,
    com o mesmo significado de `skills`. Os nomes são os arquivos sem o sufixo.
- `agents` (opcional): `target_subdir` e `names` (habilitados), mais `disabled`.
  Cria um link por agente. Por padrão a fonte é `agents/<nome>.md`; formatos
  próprios do consumidor declaram `source_subdir`, `source_suffix` e `target_suffix`.

Regras de `names` e `disabled`: o validador falha se um item citado não existir
no hub, se um item estiver nos dois ou se algum dos dois não for uma lista. Um item que
existe no hub e não está em `names` simplesmente não é ligado.

Não há comentários em JSON; por isso `disabled` existe: é o lugar de registrar
o que foi deixado de fora de propósito. Para desligar um item, mova-o de `names`
para `disabled` e rode `make sync-<nome>`; o link vira órfão e é removido, se
ainda for o que o hub criou.

## Skills globais

Toda skill mora em `skills/<nome>/` e é descoberta, não registrada: é skill todo
diretório que contém um `SKILL.md`. O nome do diretório, o `name:` do frontmatter e
a chave em `skills/skills.lock.json` são iguais. O lock registra a proveniência:
`origin: own` para skill autoral, ou `origin: upstream` com `repo`, `path`, `ref`,
`fetched`, `license`, `local_changes` e `notes` (use `null` no que não se sabe).
A origem vem só do lock, nunca do nome.

O agente carrega só o nome e a descrição de cada skill; o corpo entra quando ela é
invocada, então ter várias skills conectadas custa pouco contexto. Escreva a
`description` curta e com gatilhos claros.

## Agentes (opcional)

Um agente é um arquivo `agents/<nome>.md` com frontmatter (`name`, `description` e,
opcionalmente, `model` e `tools`) e o prompt de sistema no corpo. Serve para delegar
uma tarefa a um contexto próprio. Diferente de uma skill, é um **arquivo**, não uma pasta.

- São agentes todos os `agents/*.md`, exceto `README.md` e nomes iniciados por `.` ou `_`.
- O validador exige `name` igual ao nome do arquivo e uma `description`.
- A proveniência fica em `agents/agents.lock.json` (`schema_version` e `agents`, mesmos
  campos do lock de skills).
- A pasta `agents/` é opcional: sem agentes e sem lock, nada é validado nem ligado.
  Quando o primeiro agente for adicionado, o lock passa a ser obrigatório.
- Um agente só chega ao consumidor depois de listado em `agents.names` do
  `integration.json` e de um `sync`.

O hub não traz agentes por padrão. Veja o exemplo mínimo no
[README da raiz](../README.md#agentes).

## Conectar, verificar e desconectar

`python3 integrations/scripts/agents_config.py` é a interface única do ciclo de vida
da **conexão** entre este repositório e um consumidor já instalado. Nunca
instala, atualiza ou remove o consumidor em si.

- **`connect <nome>`**: cria os links declarados e grava um recibo em
  `~/.agents-config/receipts/<nome>.json` com a lista exata do que criou. É
  idempotente. Se o destino já existir como arquivo real ou symlink para outro
  conteúdo, recusa e falha, sem deixar conexão parcial.
- **`plan <nome>`**: o mesmo preflight do `connect`, sem escrever links nem recibo.
- **`status`**: por integração, se está conectada, se algum link sumiu ou aponta para
  outro lugar (`drifted`), se a origem foi apagada e se o manifesto mudou desde a
  última conexão (nesse caso, sugere `sync`).
- **`doctor`**: o relatório do `status` mais uma seção `environment`: as mesmas
  checagens do `validate` e o install home existente e gravável. Sai com
  código 1 se algo falhar.
- **`sync <nome>`**: refaz os links a partir do manifesto atual e remove os órfãos do
  recibo anterior, somente se ainda apontarem para o que foi registrado.
- **`disconnect <nome>`**: remove só os links do recibo (com a mesma checagem) e o recibo.
- **`validate`**: valida `integration.json`, skills, agentes e locks.

O recibo é estado local, nunca versionado. Numa máquina nova, `connect` reconstrói tudo
a partir dos `integration.json`.

Não crie wrapper escrito à mão por consumidor (`bootstrap-<nome>.sh`, alvo
`connect-cursor` fixo no `Makefile`). O `Makefile` da raiz descobre os consumidores
pelos `config/*/integration.json`, então `make connect-<nome>`, `plan-<nome>`,
`sync-<nome>`, `disconnect-<nome>`, `status`, `doctor` e `connect-all` passam a
existir para qualquer pasta nova. Ele não tem lógica própria: só chama a CLI, que é
o contrato.

## Adicionando um novo adaptador

Veja [`config/template/README.md`](./template/README.md).

## Fronteira de versionamento

Permanecem versionados: skills (com `skills/skills.lock.json`), definições de agentes,
prompts reutilizáveis, adaptadores, `integration.json`, scripts e testes.

Permanecem só no ambiente local: credenciais e tokens, estado de autenticação,
histórico de conversas, logs e caches, estado de interface específico da máquina e
os recibos de conexão.

## Fora do escopo

- Instalar, atualizar ou gerenciar o consumidor (Cursor ou outro): o hub conecta o
  repositório a uma instalação que já existe.
- Interfaces que não leem configuração local em `$HOME`. Os links só servem a quem lê
  arquivos sob `$HOME`; não presuma que `connect <consumidor>` generaliza.
- Checar a versão do consumidor instalado: decisão para manter o `doctor` simples.
- Escopar skill por projeto pelo hub: o symlink em `$HOME` é global, e o custo de
  contexto (algumas dezenas a poucas centenas de tokens por skill) é aceito.
- Versionar credenciais, sessões ou caches.

## Relacionado

- [Adaptador do Cursor](./cursor/README.md)
