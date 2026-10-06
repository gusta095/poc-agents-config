# Template de adaptador

Referência mínima para integrar um novo consumidor. Copie a forma, não o
conteúdo: o adaptador real fica em `config/<nome>/`, junto do seu
`integration.json`. O contrato completo está em [`config/README.md`](../README.md).

## 1. Declaração da integração

Crie `config/<nome>/integration.json`. O `name` tem que ser igual ao nome da
pasta. Exemplo para um consumidor sem arquivo global de regras (como o Cursor):

```json
{
  "schema_version": 1,
  "name": "<nome>",
  "home": {
    "home_env": ["AGENTS_CONFIG_<NOME>_HOME"],
    "home_default": ".<nome>"
  },
  "skills": {
    "base": "entry_home",
    "target_subdir": "skills",
    "names": ["<skill-habilitada>"],
    "disabled": []
  }
}
```

Blocos opcionais, com o mesmo padrão `names` (habilitados) e `disabled`
(desligados de propósito):

```json
"commands": {
  "source_dir": "commands",
  "target_subdir": "commands",
  "names": ["<comando>"],
  "disabled": []
},
"agents": {
  "target_subdir": "agents",
  "names": [],
  "disabled": []
}
```

Se o consumidor tem um arquivo global de regras em disco, declare-o em `entry`
(`source`, relativo à pasta do adaptador, e `target_name`). Nesse caso `entry.home_env`
e `entry.home_default` substituem o bloco `home`, e o arquivo de entrada deve ser mínimo.

Ajuste `skills.base` e `skills.target_subdir` conforme onde o consumidor descobre skills:
dentro do próprio diretório (`"entry_home"`) ou relativo ao `HOME` (`"install_home"`).

## 2. Conectar

```bash
make plan-<nome>      # mostra o que seria criado
make connect-<nome>
```

Equivale a `python3 integrations/scripts/agents_config.py connect <nome>`. O
`Makefile` descobre a pasta nova sozinho: não crie um wrapper por consumidor nem
edite o `Makefile`.

## 3. Validar

```bash
make check
```
