# Provides short commands for managing and checking the local Docker services.

.PHONY: setup sync lock lint rankings-preview rankings-ingest dbt-debug dbt-build dbt-preview dbt-preview-latest duckdb-ui build up down status logs config minio-ui airflow-init airflow-ui airflow-logs airflow-dags

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

dbt-debug: build
	docker compose up minio-init
	docker compose run --rm dbt debug

dbt-build: build
	docker compose up minio-init
	docker compose run --rm dbt build

dbt-preview: build
	docker compose up minio-init
	docker compose run --rm dbt show --select stg_nflverse__ff_rankings --limit 5

dbt-preview-latest: build
	docker compose up minio-init
	docker compose run --rm dbt show --select int_ff_rankings__latest_redraft --limit 5

duckdb-ui:
	@set -a; if [ -f .env ]; then . ./.env; fi; set +a; uv run python -m ffguru.duckdb_ui

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
