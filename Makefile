.PHONY: up down api web seed test
up:
	docker compose up --build
down:
	docker compose down
api:
	cd apps/api && uvicorn app.main:app --reload
web:
	cd apps/web && npm run dev
seed:
	cd apps/api && python -m app.seed
test:
	cd apps/api && pytest -q
