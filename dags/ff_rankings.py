"""Defines the daily Airflow workflow that snapshots draft rankings to bronze storage."""

from datetime import UTC, datetime, timedelta

from airflow.sdk import dag, get_current_context, task


@dag(
    dag_id="ff_rankings_bronze",
    schedule="0 0 * * *",
    start_date=datetime(2026, 1, 1, tzinfo=UTC),
    catchup=False,
    max_active_runs=1,
    tags=["bronze", "nflverse"],
)
def ff_rankings_bronze():
    @task(retries=2, retry_delay=timedelta(minutes=5))
    def ingest_rankings() -> dict[str, str | int | bool]:
        from ffguru.tasks.ingestion.ff_rankings import ingest_draft_rankings

        context = get_current_context()
        snapshot_date = context["logical_date"].date()
        result = ingest_draft_rankings(snapshot_date=snapshot_date)
        print(result)
        return result

    ingest_rankings()


ff_rankings_bronze()
