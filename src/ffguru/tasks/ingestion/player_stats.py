"""Loads raw current-season weekly player statistics from nflverse."""

import os
from datetime import UTC, date, datetime

import nflreadpy
import polars as pl

from ffguru.storage.minio import write_parquet_if_absent


def load_weekly_player_stats() -> pl.DataFrame:
    return nflreadpy.load_player_stats(seasons=None, summary_level="week")


def _get_single_season(stats: pl.DataFrame) -> int:
    if "season" not in stats.columns:
        raise ValueError("Player stats are missing the season column")

    seasons = stats.get_column("season").drop_nulls().unique().to_list()
    if len(seasons) != 1:
        raise ValueError(f"Expected player stats for exactly one season, received: {seasons}")

    return int(seasons[0])


def ingest_weekly_player_stats(
    snapshot_date: date | None = None,
) -> dict[str, str | int | bool]:
    stats = load_weekly_player_stats()
    season = _get_single_season(stats)
    effective_date = snapshot_date or datetime.now(UTC).date()
    bucket = os.environ.get("BRONZE_BUCKET", "bronze")
    object_key = (
        "nflverse/player_stats/summary_level=week/"
        f"season={season}/snapshot_date={effective_date.isoformat()}/player_stats.parquet"
    )
    created = write_parquet_if_absent(stats, bucket, object_key)

    return {
        "uri": f"s3://{bucket}/{object_key}",
        "rows": stats.height,
        "columns": stats.width,
        "created": created,
    }
