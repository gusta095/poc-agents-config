# Interface de comandos do repositório. Todo alvo é um atalho para a CLI
# (integrations/scripts/agents_config.py) ou para as ferramentas de qualidade:
# o Makefile não tem lógica própria. O contrato é a CLI; sem `make`, chame-a
# diretamente. Os consumidores vêm de config/*/integration.json, então
# adicionar uma pasta de integração cria os alvos `<comando>-<nome>` sozinho.

CLI := python3 integrations/scripts/agents_config.py
CONSUMERS := $(sort $(patsubst config/%/integration.json,%,$(wildcard config/*/integration.json)))

.DEFAULT_GOAL := help

##@ Conexão

.PHONY: status
status: ## Estado da conexão de cada consumidor
	$(CLI) status

.PHONY: doctor
doctor: ## Status mais checagens de ambiente (layout do hub, install home)
	$(CLI) doctor

connect-%: ## Conecta um consumidor (ex.: connect-cursor)
	$(CLI) connect $*

plan-%: ## Mostra o que connect faria, sem alterar nada
	$(CLI) plan $*

sync-%: ## Refaz links e registros após mudar o integration.json
	$(CLI) sync $*

disconnect-%: ## Remove os links que o hub criou
	$(CLI) disconnect $*

.PHONY: connect-all
connect-all: $(addprefix connect-,$(CONSUMERS)) ## Conecta todos os consumidores

##@ Qualidade

.PHONY: check
check: validate test ## Roda validate e todos os testes

.PHONY: validate
validate: ## Valida os integration.json, as skills e os agentes
	$(CLI) validate

.PHONY: test
test: test-core test-skills ## Roda todos os testes

.PHONY: test-core
test-core: ## Testa integrações e automações do repositório
	python3 -m unittest discover -s integrations/tests
	python3 -m unittest discover -s tests

.PHONY: test-skills
test-skills: ## Descobre e testa todas as skills que contêm Python
	python3 scripts/ci/discover_skill_tests.py --run

##@ Manutenção

.PHONY: clean
clean: ## Remove __pycache__
	find . -type d -name '__pycache__' -not -path './.git/*' -print -prune -exec rm -rf '{}' \;

.PHONY: help
help: ## Exibe esta mensagem
	@awk 'BEGIN {FS = ":.*## "; printf "\n\033[1magents-config\033[0m\n"} \
		/^##@/ {printf "\n\033[1m%s\033[0m\n", substr($$0, 5)} \
		/^[a-zA-Z_%-]+:.*## / {name = $$1; gsub(/%/, "<nome>", name); printf "  make %-18s %s\n", name, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "Consumidores descobertos: $(CONSUMERS)"
	@echo ""
