# Contrato do plano de execução

O plano é o handoff entre quem decide, quem planeja e quem executa. Seu conteúdo
mostra o estado desejado atual; a execução se verifica pelos critérios, sem
transformar o plano em registro do que aconteceu.

## Estrutura mínima

Registre, de modo proporcional ao trabalho:

1. objetivo e resultado final esperado;
2. estado atual relevante e escopo (inclusive o que fica fora);
3. decisões vigentes, premissas, perguntas abertas e limitações da análise;
4. artefatos selecionados e estrutura afetada, quando relevantes;
5. critérios globais de conclusão;
6. fases, tarefas, dependências e verificação;
7. riscos reais e como detectá-los ou recuperar, quando relevantes.

**Limitações** identifica o que ainda não foi lido ou verificado e por quê.
Atualize a seção quando a situação mudar; não preserve ressalvas superadas.

Não inclua registro de mudanças, linha do tempo, status de execução, evidências
de rodadas passadas ou ponto de retomada no plano. Esses dados não definem o
estado desejado. Não crie arquivo de histórico por padrão. A mesma regra vale para todos os
artefatos de planejamento, inclusive `.specs/feature-<nome>.md`.

## Fases

Cada fase termina em resultado observável e informa:

- objetivo e resultado esperado;
- dependências ou critério de entrada;
- critério de conclusão;
- tarefas que produzem a entrega.

Detalhe completamente apenas a fase pronta para execução. Resuma as futuras
até que as anteriores estejam validadas.

## Tarefas

Cada tarefa deve poder ser entregue a um agente sem reconstruir a conversa.
Registre apenas o que for útil para executá-la:

- executor recomendado, quando útil;
- objetivo e o que fazer;
- como fazer, no nível de abordagem e sem antecipar código desnecessário;
- arquivos a criar ou modificar;
- restrições e decisões vigentes;
- dependências e paralelismo real;
- resultado esperado, verificação e critério de pronto.

Prefira uma unidade focada com resultado verificável. Não use duração arbitrária
em minutos como medida de granularidade.

## Handoff e mudanças

O executor respeita o escopo, pergunta quando falta uma decisão relevante,
verifica o resultado e relata achados no handoff. Quem coordena compara o
resultado com os critérios do plano. Falha de verificação permanece pendente na
execução; não vira “concluída” porque o plano diz que deveria funcionar.

Quando uma decisão mudar, revise o plano e os demais artefatos normativos em
`.specs/` para que descrevam somente a regra vigente. Aponte os testes e o
código que precisarão acompanhar a mudança. A validação do diff, dos comandos
e do trabalho concluído pertence ao handoff, PR ou ferramenta de execução.

## Checklist

- [ ] O objetivo, o resultado final e os critérios de conclusão são verificáveis.
- [ ] Escopo e fora do escopo estão claros.
- [ ] Artefatos foram selecionados pela necessidade e ficam em `.specs/`.
- [ ] Perguntas abertas não viraram decisões silenciosas.
- [ ] Fatos não confirmados e limitações atuais estão identificados.
- [ ] Cada fase possui resultado e critério de conclusão.
- [ ] A fase ativa está detalhada e as futuras estão resumidas.
- [ ] Cada tarefa diz o que fazer, como abordar e qual resultado produzir.
- [ ] Cada tarefa possui verificação, critério de pronto e dependências.
- [ ] Paralelismo não cria disputa pelos mesmos arquivos ou decisões.
- [ ] Um executor consegue assumir a tarefa sem reconstruir a conversa.
- [ ] Não há regra antiga, histórico ou status de execução misturados ao plano.
- [ ] As regras e os critérios de aceite foram revisados antes da implementação.
- [ ] Funcionalidades fora da base têm `feature-<nome>.md`, sem status ou histórico.
- [ ] Mudanças compartilhadas estão alinhadas entre feature, base, design e plano.
- [ ] Critérios possuem verificação capaz de provar o comportamento e suas interações.
- [ ] A validação independente e o aceite humano têm responsáveis definidos.
