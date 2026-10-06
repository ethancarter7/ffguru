"""Tests the weekly player-data Airflow DAG structure."""

import importlib.util
from pathlib import Path


def _load_dag_module():
    dag_path = Path(__file__).parents[1] / "dags" / "player_data.py"
    spec = importlib.util.spec_from_file_location("player_data_dag", dag_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_player_data_dag_configuration():
    dag = _load_dag_module().player_data_bronze()

    assert dag.dag_id == "player_data_bronze"
    assert str(dag.schedule) == "0 12 * * 3"
    assert dag.catchup is False
    assert dag.max_active_runs == 1
    assert set(dag.task_ids) == {
        "ingest_player_stats",
        "ingest_player_ids",
        "build_player_stats_models",
    }


def test_player_data_tasks_are_parallel_and_retryable():
    dag = _load_dag_module().player_data_bronze()

    stats_task = dag.get_task("ingest_player_stats")
    ids_task = dag.get_task("ingest_player_ids")
    dbt_task = dag.get_task("build_player_stats_models")

    assert stats_task.upstream_task_ids == set()
    assert stats_task.downstream_task_ids == {"build_player_stats_models"}
    assert stats_task.retries == 2
    assert ids_task.upstream_task_ids == set()
    assert ids_task.downstream_task_ids == set()
    assert ids_task.retries == 2
    assert dbt_task.upstream_task_ids == {"ingest_player_stats"}
    assert dbt_task.downstream_task_ids == set()
    assert dbt_task.retries == 1
