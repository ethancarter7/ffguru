"""Runs dbt transformations as subprocesses that Airflow can monitor."""

import os
import subprocess
from pathlib import Path


def build_dbt_project(
    project_dir: str | Path = "/opt/airflow/dbt",
    select: str | None = None,
) -> None:
    project_path = Path(project_dir)
    profiles_dir = os.environ.get("DBT_PROFILES_DIR", str(project_path))
    command = [
        "dbt",
        "build",
        "--project-dir",
        str(project_path),
        "--profiles-dir",
        profiles_dir,
    ]
    if select is not None:
        command.extend(["--select", select])

    subprocess.run(command, check=True)
