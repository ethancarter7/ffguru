"""Loads unmodified fantasy-football draft rankings from nflverse."""

import os
from datetime import UTC, date, datetime

import nflreadpy
import polars as pl

from ffguru.storage.minio import write_parquet_if_absent


def load_draft_rankings() -> pl.DataFrame:
    """
    Type of rankings to load: 
    - "draft": Draft rankings/projections 
    - "week": Weekly rankings/projections 
    - "all": All historical rankings/projections
    """
    return nflreadpy.load_ff_rankings(type="draft")


def ingest_draft_rankings(snapshot_date: date | None = None) -> dict[str, str | int | bool]:
    effective_date = snapshot_date or datetime.now(UTC).date()
    bucket = os.environ.get("BRONZE_BUCKET", "bronze")
    object_key = (
        "nflverse/ff_rankings/type=draft/"
        f"snapshot_date={effective_date.isoformat()}/ff_rankings.parquet"
    )
    rankings = load_draft_rankings()
    created = write_parquet_if_absent(rankings, bucket, object_key)

    return {
        "uri": f"s3://{bucket}/{object_key}",
        "rows": rankings.height,
        "columns": rankings.width,
        "created": created,
    }
