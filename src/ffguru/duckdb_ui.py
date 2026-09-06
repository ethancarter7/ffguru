"""Launches DuckDB's local browser UI with access to the database and MinIO bronze data."""

import os
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_PATH = PROJECT_ROOT / "data" / "ffguru.duckdb"
EXTENSION_PATH = PROJECT_ROOT / "data" / ".duckdb" / "extensions"


def main() -> None:
    connection = duckdb.connect(
        str(DATABASE_PATH),
        config={"extension_directory": str(EXTENSION_PATH)},
    )
    connection.install_extension("httpfs")
    connection.load_extension("httpfs")
    connection.execute(
        """
        create or replace secret duckdb_ui_minio (
            type s3,
            key_id ?,
            secret ?,
            region 'us-east-1',
            endpoint ?,
            url_style path,
            use_ssl false
        )
        """,
        [
            os.getenv("MINIO_ROOT_USER", "minioadmin"),
            os.getenv("MINIO_ROOT_PASSWORD", "minioadmin"),
            os.getenv("MINIO_DUCKDB_UI_ENDPOINT", "localhost:9000"),
        ],
    )
    connection.execute("call start_ui()")

    try:
        input("DuckDB UI is running. Press Enter to stop.\n")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
