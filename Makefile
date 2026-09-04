# Provides short commands for managing and checking the local Docker services.

.PHONY: setup sync lock lint rankings-preview rankings-ingest build up down status logs config minio-ui airflow-init airflow-ui airflow-logs airflow-dags

setup:
	uv python install 3.12
	uv sync

sync:
	uv sync

lock:
	uv lock

lint:
	uv run ruff check .

rankings-preview:
	uv run python -c 'from ffguru.tasks.ingestion.ff_rankings import load_draft_rankings; rankings = load_draft_rankings(); print(rankings.head()); print(f"rows={rankings.height}, columns={rankings.width}")'

rankings-ingest: build
	docker compose up minio-init
	docker compose run --rm --no-deps --entrypoint python airflow-api-server -c 'from ffguru.tasks.ingestion.ff_rankings import ingest_draft_rankings; print(ingest_draft_rankings())'

build:
	docker compose build airflow-api-server

up: build
	docker compose up -d --no-build

down:
	docker compose down

status:
	docker compose ps

logs:
	docker compose logs -f

config:
	docker compose config --quiet

minio-ui: up
	open http://localhost:9001

airflow-init: build
	docker compose up --no-build airflow-init

airflow-ui: up
	open http://localhost:8080

airflow-logs:
	docker compose logs -f airflow-api-server airflow-scheduler airflow-dag-processor

airflow-dags: up
	docker compose exec airflow-api-server airflow dags list
