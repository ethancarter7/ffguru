# ffguru

## Python environment

The project uses `uv` to manage Python 3.12, the local `.venv`, and locked package versions. `pyproject.toml` lists direct dependencies, while the generated `uv.lock` records the complete reproducible dependency graph.

Create the environment for the first time:

```bash
make setup
```

After changing dependencies in `pyproject.toml`, regenerate the lockfile with `make lock` and update the environment with `make sync`. Run the Python linter with `make lint`.

## Local storage

The first checkpoint runs two persistent services and one setup task:

- **MinIO** provides an S3-compatible object store for immutable bronze data.
- **Postgres** will store Airflow's internal metadata when Airflow is added.
- **minio-init** creates the `bronze` bucket and then exits; rerunning it is safe because the operation is idempotent.

`compose.yaml` defines the containers, ports, health checks, volumes, and shared Docker network. `.env.example` documents the local configuration without committing a real `.env` file.

### Start the services

The Compose file has development defaults, so an environment file is optional. To customize the credentials, copy `.env.example` to `.env` and edit the copy.

```bash
make up
make status
```

Open the MinIO console at [http://localhost:9001](http://localhost:9001). With the defaults, sign in with `minioadmin` for both the username and password.

```bash
make minio-ui
```

This command ensures the Docker services are running and opens the MinIO console in the default browser on macOS.

The object browser should contain a bucket named `bronze`. This bucket will hold unchanged snapshots downloaded from external sources.

Postgres listens on `localhost:5433` because another local Docker project already uses host port `5432`. Other project containers will reach it as `postgres:5432` on the shared network.

### Stop the services

```bash
make down
```

Named volumes preserve stored data when the containers stop. `docker compose down --volumes` also deletes that data, so do not use that option unless you intend to reset the environment.

## Airflow runtime

Airflow orchestrates scheduled workflows while Postgres records their operational state. This local installation uses `LocalExecutor`, so tasks run through the scheduler without Redis or separate worker containers.

The runtime contains four Airflow services:

- **airflow-init** applies metadata database migrations and creates the local administrator account, then exits.
- **airflow-api-server** serves the web interface and API.
- **airflow-scheduler** determines which task instances are ready to run and executes them locally.
- **airflow-dag-processor** reads Python files from `dags/` and records their workflow structure.

Initialize Airflow explicitly when setting up a new metadata database:

```bash
make airflow-init
```

Start the complete environment and open the Airflow interface:

```bash
make airflow-ui
```

The interface is available at [http://localhost:8080](http://localhost:8080). With the development defaults, use `airflow` for both the username and password.

To follow only the Airflow service logs, run:

```bash
make airflow-logs
```

## First workflow

`dags/airflow_learning.py` defines two tasks: one returns a short message and the second prints it. Airflow stores the small returned value as an XCom and uses the declared dependency to run the tasks in order.

List the DAGs recognized by Airflow:

```bash
make airflow-dags
```

Open the Airflow interface with `make airflow-ui`, select `airflow_learning`, unpause it, and use the play button to trigger a manual run. The Graph view shows the dependency, while each task instance contains its own status and logs.

## dbt and DuckDB

dbt reads bronze Parquet snapshots from MinIO and creates analytics models in a persistent DuckDB database. Staging selects the useful source fields, while `silver.int_ff_rankings__latest_redraft` exposes the newest overall redraft rankings.

```bash
make dbt-debug
make dbt-build
make dbt-preview
make dbt-preview-latest
make duckdb-ui
```

`dbt-debug` validates the profile and database connection, `dbt-build` creates models and runs their tests, and the preview commands display sample staging or latest-redraft rows. `duckdb-ui` opens DuckDB's local browser interface for exploring schemas, previewing data, and running SQL; keep its terminal open while using the interface and press Enter to stop it.

The scheduled `ff_rankings_bronze` Airflow DAG runs `dbt build` after a successful bronze ingestion. The separate Make commands remain useful for development and troubleshooting.

## Personal rankings

The local Flask app freezes the latest 200 QB, RB, WR, and TE rankings into a separate DuckDB database, then builds a personal board from blind pairwise choices.

```bash
make rankings-ui
make rankings-export
make rankings-logs
make rankings-stop
```

The comparison screen supports choose, skip, and undo. The rankings screen shows the evolving board, while the CSV export contains every latest intermediate ranking plus a nullable `vs_ecr` column; reset is the only action that replaces the frozen source snapshot.
