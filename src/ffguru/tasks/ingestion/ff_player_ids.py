"""Loads the raw fantasy-football player identifier map from nflverse."""

import os
from datetime import UTC, date, datetime

import nflreadpy
import polars as pl

from ffguru.storage.minio import write_parquet_if_absent


def load_ff_player_ids() -> pl.DataFrame:
    return nflreadpy.load_ff_playerids()


def ingest_ff_player_ids(snapshot_date: date | None = None) -> dict[str, str | int | bool]:
    player_ids = load_ff_player_ids()
    if player_ids.is_empty():
        raise ValueError("Fantasy football player ID data is empty")

    effective_date = snapshot_date or datetime.now(UTC).date()
    bucket = os.environ.get("BRONZE_BUCKET", "bronze")
    object_key = (
        "nflverse/ff_playerids/"
        f"snapshot_date={effective_date.isoformat()}/ff_playerids.parquet"
    )
    created = write_parquet_if_absent(player_ids, bucket, object_key)

    return {
        "uri": f"s3://{bucket}/{object_key}",
        "rows": player_ids.height,
        "columns": player_ids.width,
        "created": created,
    }
