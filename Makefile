.PHONY: dev backend frontend test lint

ENV_FILE := .env.development

dev: $(ENV_FILE)
	./scripts/dev.sh

backend: $(ENV_FILE)
	./scripts/backend.sh

frontend: $(ENV_FILE)
	./scripts/frontend.sh

test:
	./scripts/test.sh

lint:
	./scripts/lint.sh
