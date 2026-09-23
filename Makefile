# Provides short commands for managing and checking the local Docker services.

.PHONY: setup sync lock lint test rankings-preview rankings-ingest player-data-preview player-data-ingest rankings-ui rankings-export rankings-stop rankings-logs dbt-debug dbt-build dbt-preview dbt-preview-latest duckdb-ui build up down status logs config minio-ui airflow-init airflow-ui airflow-logs airflow-dags

# Installs Python 3.12 and creates the local project environment.
setup:
	uv python install 3.12
	uv sync

# Synchronizes the local environment with the locked dependencies.
sync:
	uv sync

# Recalculates the dependency lockfile from pyproject.toml.
lock:
	uv lock

# Checks the Python code for linting problems without changing files.
lint:
	uv run ruff check .

# Runs the automated Python test suite.
test:
	uv run pytest

# Downloads draft rankings locally and prints a small sample.
rankings-preview:
	uv run python -c 'from ffguru.tasks.ingestion.ff_rankings import load_draft_rankings; rankings = load_draft_rankings(); print(rankings.head()); print(f"rows={rankings.height}, columns={rankings.width}")'

# Loads today's draft-ranking snapshot into the MinIO bronze bucket.
rankings-ingest: build
	docker compose up minio-init
	docker compose run --rm --no-deps --entrypoint python airflow-api-server -c 'from ffguru.tasks.ingestion.ff_rankings import ingest_draft_rankings; print(ingest_draft_rankings())'

# Downloads current player stats and IDs locally and prints small samples.
player-data-preview:
	uv run python -c 'from ffguru.tasks.ingestion.player_stats import load_weekly_player_stats; from ffguru.tasks.ingestion.ff_player_ids import load_ff_player_ids; stats = load_weekly_player_stats(); player_ids = load_ff_player_ids(); print(stats.head()); print(f"player stats: rows={stats.height}, columns={stats.width}"); print(player_ids.head()); print(f"player IDs: rows={player_ids.height}, columns={player_ids.width}")'

# Loads today's player-stat and player-ID snapshots into the MinIO bronze bucket.
player-data-ingest: build
	docker compose up minio-init
	docker compose run --rm --no-deps --entrypoint python airflow-api-server -c 'from ffguru.tasks.ingestion.player_stats import ingest_weekly_player_stats; from ffguru.tasks.ingestion.ff_player_ids import ingest_ff_player_ids; print(ingest_weekly_player_stats()); print(ingest_ff_player_ids())'

# Starts the personal rankings app and opens it in the browser.
rankings-ui: build
	docker compose up -d --no-build --wait rankings-app
	open http://localhost:5000

# Generates the latest rankings CSV with the nullable personal vs_ecr column.
rankings-export: build
	docker compose up -d --no-build --wait rankings-app
	curl --fail --silent --show-error --output data/latest_ff_rankings_with_personal.csv http://localhost:5000/rankings.csv

# Stops the personal rankings app without deleting its saved data.
rankings-stop:
	docker compose stop rankings-app

# Follows the personal rankings app logs until interrupted.
rankings-logs:
	docker compose logs -f rankings-app

# Validates the dbt project, profile, dependencies, and DuckDB connection.
dbt-debug: build
	docker compose up minio-init
	docker compose run --rm dbt debug

# Builds every dbt model and runs all configured data tests.
dbt-build: build
	docker compose up minio-init
	docker compose run --rm dbt build

# Displays five rows from the cleaned staging rankings model.
dbt-preview: build
	docker compose up minio-init
	docker compose run --rm dbt show --select stg_nflverse__ff_rankings --limit 5

# Displays five rows from the latest overall redraft model.
dbt-preview-latest: build
	docker compose up minio-init
	docker compose run --rm dbt show --select int_ff_rankings__latest_redraft --limit 5

# Opens DuckDB's local browser interface for exploring the analytics database.
duckdb-ui:
	@set -a; if [ -f .env ]; then . ./.env; fi; set +a; uv run python -m ffguru.duckdb_ui

# Builds the shared local image containing Airflow and the project code.
build:
	docker compose build airflow-api-server

# Builds the image and starts the default platform services in the background.
up: build
	docker compose up -d --no-build

# Stops and removes the project containers while preserving persistent data.
down:
	docker compose down

# Shows the current state and health of running project containers.
status:
	docker compose ps

# Follows logs from all running Compose services until interrupted.
logs:
	docker compose logs -f

# Validates the resolved Docker Compose configuration.
config:
	docker compose config --quiet

# Starts the platform and opens the MinIO management interface.
minio-ui: up
	open http://localhost:9001

# Initializes Airflow's metadata database and administrator account.
airflow-init: build
	docker compose up --no-build airflow-init

# Starts the platform and opens the Airflow interface.
airflow-ui: up
	open http://localhost:8080

# Follows logs from the three long-running Airflow services.
airflow-logs:
	docker compose logs -f airflow-api-server airflow-scheduler airflow-dag-processor

# Lists every DAG currently recognized by Airflow.
airflow-dags: up
	docker compose exec airflow-api-server airflow dags list
