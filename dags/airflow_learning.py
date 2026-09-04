"""Defines a manual two-task workflow for learning Airflow's basic execution model."""

from datetime import UTC, datetime

from airflow.sdk import dag, task


@dag(
    dag_id="airflow_learning",
    schedule=None,
    start_date=datetime(2026, 1, 1, tzinfo=UTC),
    catchup=False,
    tags=["learning"],
)
def airflow_learning():
    @task
    def create_message() -> str:
        return "The first Airflow task completed successfully."

    @task
    def display_message(message: str) -> None:
        print(message)

    display_message(create_message())


airflow_learning()
