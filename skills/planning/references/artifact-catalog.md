# Catálogo de artefatos

Artefatos reduzem incerteza; não são documentação obrigatória. Um artefato
torna-se necessário somente quando sua ausência deixa sem resposta uma decisão
que afeta a execução ou a validação. Os arquivos documentais selecionados pelo
planejamento ficam em `.specs/`; código e testes permanecem nos diretórios do
projeto.

| Artefato | Entrega | Uso |
| --- | --- | --- |
| Requisitos de produto (PRD) | problema, consumidores, objetivos, requisitos e métricas | definir o que construir e por quê |
| Requisitos técnicos (TRD) | arquitetura, integrações, restrições e requisitos não funcionais | definir limites técnicos |
| Fluxo da solução | jornada de cada ator relevante — consumidor, operador, sistema, CLI, agente ou automação | explicar o comportamento ponta a ponta |
| UI/UX e identidade | wireframes, navegação, componentes e referências visuais | orientar projetos com interface |
| Modelo de dados | entidades, relacionamentos, estado e migrações | orientar soluções com persistência |
| Contratos e interfaces | APIs, schemas, eventos, comandos ou configurações | definir comunicação entre componentes |
| Desenho de arquitetura | componentes, responsabilidades e dependências | mostrar a estrutura da solução |
| Estratégia de testes | cenários, níveis e evidências esperadas | definir como validar comportamento |
| Plano de execução | fases, tarefas, dependências e critérios | transformar decisões em trabalho |
| Spec de feature | comportamento, impactos, tarefas e aceite em `feature-<nome>.md` | planejar funcionalidade acrescentada ao escopo base |

## Seleção

Avalie:

1. Existe usuário ou consumidor definido?
2. Existe interface, jornada ou fluxo operacional relevante? Quando quem
   consome a solução e quem a opera ou executa forem atores diferentes (ex.:
   um portal consumindo a API vs. a pessoa que sobe o processo localmente com
   suas credenciais), trate as duas jornadas em separado.
3. Existe persistência ou modelo de dados?
4. Existem integrações, contratos ou dependências externas?
5. Existem decisões técnicas difíceis de reverter?
6. Há requisitos relevantes de segurança, custo, operação ou observabilidade?

Classifique o que for relevante como `existente`, `a criar` ou `adiado`,
indicando quando um adiamento precisa ser resolvido. Omita o que não se aplica,
exceto quando a ausência consciente puder gerar dúvida.

Vários conteúdos podem viver no mesmo documento de design ou plano. Separe
arquivos somente quando isso melhorar leitura, manutenção ou reutilização.
