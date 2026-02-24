.PHONY: up down dev seed test migrate logs clean

up:
	docker compose up -d

down:
	docker compose down

dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up

seed:
	docker compose exec backend python -m app.seed

test:
	docker compose exec backend pytest

migrate:
	docker compose exec backend alembic -c alembic/alembic.ini upgrade head

logs:
	docker compose logs -f

clean:
	docker compose down -v
