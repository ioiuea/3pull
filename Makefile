FRONTEND_DIR := apps/frontend

# ------------------------------
# Frontend CI targets
# ------------------------------
.PHONY: frontend-install frontend-format frontend-format-fix frontend-lint frontend-lint-fix frontend-typecheck frontend-test frontend-ci

frontend-install:
	pnpm --dir $(FRONTEND_DIR) install --frozen-lockfile

frontend-format:
	pnpm --dir $(FRONTEND_DIR) run format

frontend-format-fix:
	pnpm --dir $(FRONTEND_DIR) run format:fix

frontend-lint:
	pnpm --dir $(FRONTEND_DIR) run lint

frontend-lint-fix:
	pnpm --dir $(FRONTEND_DIR) run lint:fix

frontend-typecheck:
	pnpm --dir $(FRONTEND_DIR) run typecheck:ci

frontend-test:
	pnpm --dir $(FRONTEND_DIR) run test:run

frontend-ci: frontend-format frontend-lint frontend-typecheck frontend-test
