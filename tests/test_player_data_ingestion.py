"""Tests current-season player statistics and player-ID bronze ingestion."""

from datetime import date

import polars as pl
import pytest

from ffguru.tasks.ingestion import ff_player_ids, player_stats


def test_load_weekly_player_stats_uses_current_season(monkeypatch):
    expected = pl.DataFrame({"season": [2026]})
    calls = []

    def fake_load_player_stats(*, seasons, summary_level):
        calls.append((seasons, summary_level))
        return expected

    monkeypatch.setattr(player_stats.nflreadpy, "load_player_stats", fake_load_player_stats)

    assert player_stats.load_weekly_player_stats().equals(expected)
    assert calls == [(None, "week")]


def test_ingest_weekly_player_stats_uses_returned_season(monkeypatch):
    frame = pl.DataFrame(
        {
            "season": [2026, 2026],
            "week": [1, 1],
            "player_id": ["one", "two"],
        }
    )
    writes = []
    monkeypatch.setenv("BRONZE_BUCKET", "test-bronze")
    monkeypatch.setattr(player_stats, "load_weekly_player_stats", lambda: frame)
    monkeypatch.setattr(
        player_stats,
        "write_parquet_if_absent",
        lambda data, bucket, key: writes.append((data, bucket, key)) or True,
    )

    result = player_stats.ingest_weekly_player_stats(date(2026, 9, 23))

    expected_key = (
        "nflverse/player_stats/summary_level=week/season=2026/"
        "snapshot_date=2026-09-23/player_stats.parquet"
    )
    assert writes == [(frame, "test-bronze", expected_key)]
    assert result == {
        "uri": f"s3://test-bronze/{expected_key}",
        "rows": 2,
        "columns": 3,
        "created": True,
    }


@pytest.mark.parametrize(
    "frame",
    [
        pl.DataFrame({"season": []}, schema={"season": pl.Int64}),
        pl.DataFrame({"season": [2025, 2026]}),
    ],
)
def test_ingest_weekly_player_stats_rejects_invalid_seasons(monkeypatch, frame):
    monkeypatch.setattr(player_stats, "load_weekly_player_stats", lambda: frame)
    monkeypatch.setattr(
        player_stats,
        "write_parquet_if_absent",
        lambda *args: pytest.fail("Invalid stats must not be written"),
    )

    with pytest.raises(ValueError, match="exactly one season"):
        player_stats.ingest_weekly_player_stats(date(2026, 9, 23))


def test_ingest_weekly_player_stats_reports_existing_snapshot(monkeypatch):
    frame = pl.DataFrame({"season": [2026]})
    monkeypatch.setattr(player_stats, "load_weekly_player_stats", lambda: frame)
    monkeypatch.setattr(player_stats, "write_parquet_if_absent", lambda *args: False)

    result = player_stats.ingest_weekly_player_stats(date(2026, 9, 23))

    assert result["created"] is False


def test_load_ff_player_ids_calls_nflreadpy(monkeypatch):
    expected = pl.DataFrame({"gsis_id": ["00-0000001"]})
    calls = []

    def fake_load_ff_playerids():
        calls.append(True)
        return expected

    monkeypatch.setattr(ff_player_ids.nflreadpy, "load_ff_playerids", fake_load_ff_playerids)

    assert ff_player_ids.load_ff_player_ids().equals(expected)
    assert calls == [True]


def test_ingest_ff_player_ids_writes_snapshot(monkeypatch):
    frame = pl.DataFrame(
        {
            "gsis_id": ["00-0000001"],
            "fantasypros_id": [123],
        }
    )
    writes = []
    monkeypatch.setenv("BRONZE_BUCKET", "test-bronze")
    monkeypatch.setattr(ff_player_ids, "load_ff_player_ids", lambda: frame)
    monkeypatch.setattr(
        ff_player_ids,
        "write_parquet_if_absent",
        lambda data, bucket, key: writes.append((data, bucket, key)) or True,
    )

    result = ff_player_ids.ingest_ff_player_ids(date(2026, 9, 23))

    expected_key = "nflverse/ff_playerids/snapshot_date=2026-09-23/ff_playerids.parquet"
    assert writes == [(frame, "test-bronze", expected_key)]
    assert result == {
        "uri": f"s3://test-bronze/{expected_key}",
        "rows": 1,
        "columns": 2,
        "created": True,
    }


def test_ingest_ff_player_ids_rejects_empty_data(monkeypatch):
    monkeypatch.setattr(ff_player_ids, "load_ff_player_ids", pl.DataFrame)
    monkeypatch.setattr(
        ff_player_ids,
        "write_parquet_if_absent",
        lambda *args: pytest.fail("Empty player IDs must not be written"),
    )

    with pytest.raises(ValueError, match="empty"):
        ff_player_ids.ingest_ff_player_ids(date(2026, 9, 23))
