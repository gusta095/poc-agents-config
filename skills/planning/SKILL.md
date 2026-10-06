---
name: planning
description: Planeje trabalho de engenharia antes da implementação e produza specs e um plano executável, proporcional e delegável em .specs/. Use quando o usuário pedir planejamento, plano de execução, roadmap detalhado ou decomposição em fases; ao iniciar projeto novo; ou diante de arquitetura, refatoração ampla, requisito ambíguo, múltiplos componentes, dependências entre agentes ou decisões difíceis de reverter. Também use para atualizar ou replanejar um plano existente. Não use para correção pequena e óbvia já pronta para implementar.
---

# Planejamento executável

Produza um contrato que outra pessoa ou agente consiga executar sem reconstruir
a conversa nem adivinhar decisões. O plano e os demais artefatos de planejamento
descrevem sempre o **estado desejado vigente**; não são diário de execução.

Vale para quem planeja (o planejador). Esta skill só define como planejar; não
define quem implementa nem como o trabalho é delegado.

## Regra central: nada falha em silêncio

Toda lacuna que afeta a execução aparece no plano. Arquivo que não foi lido,
fato que não foi verificado, contexto externo indisponível ou pergunta sem resposta
vira item em **Limitações** ou **Perguntas abertas**. Distinga o que foi
verificado do que é premissa. Ao resolver uma lacuna, atualize o estado vigente
do plano e remova a ressalva superada.

## Fluxo

1. Leia as instruções do repositório e o código real antes de propor mudanças.
2. Se já existir plano, siga [Plano existente](#plano-existente) em vez de
   começar do zero.
3. Restabeleça objetivo, resultado final esperado, escopo e critérios de
   conclusão.
4. Separe fatos, decisões vigentes, premissas e perguntas abertas. Marque como
   **não verificado** o fato que você não confirmou no repositório.
5. Trate cada dúvida pelo seu impacto:
   - **Bloqueia o plano** (altera escopo, arquitetura, experiência, dados,
     segurança, custo, autorização ou decisão difícil de reverter): não entregue
     plano completo. Devolva a pergunta com alternativas e recomendação, junto
     com o que já está estabelecido.
   - **Bloqueia só uma fase ou tarefa:** entregue o plano e identifique qual
     parte depende da resposta.
   - **Detalhe pequeno, reversível e sem impacto:** adote uma premissa explícita.
6. Selecione somente os artefatos que reduzem incerteza. Leia
   [artifact-catalog.md](references/artifact-catalog.md) ao planejar projeto
   novo, solução com vários componentes ou trabalho cujo conjunto de artefatos
   ainda não esteja claro.
7. Organize o trabalho em fases com resultados observáveis. Detalhe por inteiro
   somente a fase pronta para execução; mantenha fases futuras resumidas.
8. Quebre a fase ativa em tarefas pequenas, focadas, verificáveis e
   autossuficientes. Leia [planning-output.md](references/planning-output.md)
   antes de produzir um plano formal.
9. Identifique dependências, bloqueios e tarefas realmente paralelizáveis.
10. Revise o plano contra o checklist de
    [planning-output.md](references/planning-output.md). Antes da implementação,
    apresente as regras e os critérios de aceite completos ao responsável pela
    decisão de produto. Não implemente o produto durante o planejamento.

## Plano existente

Ao atualizar ou replanejar:

1. Leia o plano inteiro e compare suas premissas com o repositório atual.
2. Atualize diretamente escopo, decisões, tarefas, dependências e critérios
   afetados para refletir o **novo estado desejado**. Remova instruções
   superadas, perguntas respondidas e referências a comportamentos antigos.
3. Propague mudanças de regra para os outros artefatos em `.specs/` e indique
   quais testes e trechos de código precisam mudar.
4. Não mantenha “Registro de mudanças”, cronologia de decisões, status de
   tarefas executadas, resultados de comandos ou evidências históricas no
   plano. Changelog, releases, issues e histórico do Git cumprem outra função.
5. Confira que não restaram contradições entre os artefatos vigentes.

## Funcionalidades acrescentadas à base

Planeje funcionalidades que não estavam no escopo base em
`.specs/feature-<nome>.md`, com nome curto em minúsculas e hífens. Leia
[feature-spec.md](assets/feature-spec.md) como modelo proporcional à mudança.
Uma correção que apenas restaura um comportamento já especificado atualiza os
artefatos afetados; não precisa virar feature.

Descreva objetivo, comportamento vigente, arquivos/contratos afetados, interações
com features existentes, tarefas/dependências e critérios de aceite verificáveis.
Relacione a feature à spec base. Atualize também base, design e plano quando uma
regra ou contrato compartilhado mudar; não deixe regras antigas concorrentes.

Todos esses documentos mostram o estado desejado. Não inclua status de execução,
resultados de comandos, histórico ou changelog nos arquivos de feature. Evidência
e validação pertencem ao handoff, PR ou ferramenta de execução.

## Validação independente

Quando houver um revisor independente disponível no fluxo, planeje a validação
após a implementação. Os implementadores ainda verificam seu trabalho; o revisor
independente (outra sessão, pessoa ou agente) recebe specs, código e critérios em
contexto novo e reporta o resultado a quem coordena o trabalho. Reserve o aceite
subjetivo ou dependente do ambiente do usuário a quem pode verificá-lo. Critérios
não verificados permanecem pendentes; IDs de teste e suíte verde não bastam como
prova de cobertura. Inclua cenários de interação quando features compartilham estado,
contratos ou eventos. Esta skill define o planejamento, não dispara a validação.

## Contexto opcional

Quando arquitetura, infraestrutura, decisões de projeto ou padrões documentados
(docs, ADRs, notas do projeto) puderem mudar o plano, carregue esse contexto
externo. Carregue apenas o que for material para a decisão.

A falta desse contexto nunca impede o planejamento. Continue com o repositório
ativo e registre a limitação em **Limitações**.

## Local dos artefatos

Coloque **todos os arquivos documentais criados pelo planejamento** em
`.specs/` na raiz do repositório: plano, requisitos, design, contratos,
diagramas e outros artefatos selecionados. Crie a pasta se necessário. Código,
testes e arquivos da aplicação continuam nos diretórios próprios e são apenas
referenciados pelo plano.

Ao atualizar um plano existente fora de `.specs/`, mova seus artefatos de
planejamento para a pasta e ajuste os links, sem deixar cópias concorrentes.
Se o repositório tiver instrução explícita incompatível, exponha o conflito
para decisão antes de criar arquivos em outro lugar.

Use [execution-plan.md](assets/execution-plan.md) como template quando fizer
sentido. Sem ferramenta de escrita, entregue o conteúdo com caminhos em
`.specs/` e diga expressamente que nada foi gravado.

## Limites

- Não invente arquivo, comportamento, integração ou restrição não verificada.
- Não transforme artefatos opcionais em checklist burocrática.
- Não esconda perguntas relevantes dentro de tarefas.
- Não confunda roadmap com plano executável.
- Não delegue decisão aberta como detalhe de implementação.
- Não transforme o plano em acompanhamento ou histórico do projeto.
