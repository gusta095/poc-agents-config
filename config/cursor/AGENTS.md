# AGENTS.md

Instruções de entrada para agentes neste projeto.

## Skills

As skills ficam em `~/.cursor/skills/<nome>/SKILL.md` (conexão global via `make connect-cursor`) ou em `.cursor/skills/<nome>/SKILL.md` (cópia no projeto):

- `caveman-commit`: obrigatória antes de qualquer `git commit`.
- `planning`: use antes de implementar trabalho não trivial (planos, fases, decisões de arquitetura).

## Regras

- Faça a menor mudança que cumpra o pedido.
- Siga o estilo e a estrutura já existentes no projeto.
- Rode os testes e o linter relevantes antes de concluir.
- Não faça commit nem push sem pedido explícito.

Adapte este arquivo às convenções do seu projeto.
