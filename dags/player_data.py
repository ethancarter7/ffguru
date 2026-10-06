"""Defines the weekly Airflow workflow that snapshots player stats and IDs to bronze."""

from datetime import UTC, datetime, timedelta

from airflow.sdk import dag, get_current_context, task


@dag(
    dag_id="player_data_bronze",
    schedule="0 12 * * 3",
    start_date=datetime(2026, 1, 1, tzinfo=UTC),
    catchup=False,
    max_active_runs=1,
    tags=["bronze", "silver", "nflverse", "dbt", "player-data"],
)
def player_data_bronze():
    @task(retries=2, retry_delay=timedelta(minutes=5))
    def ingest_player_stats() -> dict[str, str | int | bool]:
        from ffguru.tasks.ingestion.player_stats import ingest_weekly_player_stats

        context = get_current_context()
        result = ingest_weekly_player_stats(snapshot_date=context["logical_date"].date())
        print(result)
        return result

    @task(retries=2, retry_delay=timedelta(minutes=5))
    def ingest_player_ids() -> dict[str, str | int | bool]:
        from ffguru.tasks.ingestion.ff_player_ids import ingest_ff_player_ids

        context = get_current_context()
        result = ingest_ff_player_ids(snapshot_date=context["logical_date"].date())
        print(result)
        return result

    @task(retries=1, retry_delay=timedelta(minutes=2))
    def build_player_stats_models() -> None:
        from ffguru.tasks.transformation.dbt import build_dbt_project

        build_dbt_project(select="+int_player_stats__latest")

    ingest_player_stats() >> build_player_stats_models()
    ingest_player_ids()


player_data_bronze()
