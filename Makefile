.PHONY: up down api web seed test migrate migrate-new migrate-current prod-up prod-down prod-logs

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

migrate:
	cd apps/api && alembic upgrade head

migrate-current:
	cd apps/api && alembic current

migrate-new:
	cd apps/api && alembic revision --autogenerate -m "$(name)"

prod-up:
	docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build --remove-orphans

prod-down:
	docker compose --env-file .env.production -f docker-compose.prod.yml down

prod-logs:
	docker compose --env-file .env.production -f docker-compose.prod.yml logs -f --tail=200
