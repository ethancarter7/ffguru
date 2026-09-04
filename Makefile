# Provides short commands for managing and checking the local Docker services.

.PHONY: setup sync lock lint up down status logs config minio-ui airflow-init airflow-ui airflow-logs airflow-dags

setup:
	uv python install 3.12
	uv sync

sync:
	uv sync

lock:
	uv lock

lint:
	uv run ruff check .

up:
	docker compose up -d

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

airflow-init:
	docker compose up airflow-init

airflow-ui: up
	open http://localhost:8080

airflow-logs:
	docker compose logs -f airflow-api-server airflow-scheduler airflow-dag-processor

airflow-dags: up
	docker compose exec airflow-api-server airflow dags list
