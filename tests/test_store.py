"""Tests board initialization, snapshot freezing, decisions, skipping, and undo."""

from datetime import date
from pathlib import Path

import duckdb

from ffguru.personal_rankings.store import RankingStore


def write_analytics_database(path: Path, snapshot_date: date) -> None:
    with duckdb.connect(str(path)) as connection:
        connection.execute("create schema if not exists silver")
        connection.execute("drop table if exists silver.int_ff_rankings__latest_redraft")
        connection.execute(
            """
            create table silver.int_ff_rankings__latest_redraft (
                snapshot_date date, player_id bigint, player varchar, pos varchar,
                team varchar, bye integer, ecr double, best integer, worst integer
            )
            """
        )
        rows = [
            (
                snapshot_date,
                index,
                f"Player {index}",
                ("QB", "RB", "WR", "TE")[index % 4],
                "TST",
                index % 14 + 1,
                float(index),
                max(1, index - 3),
                index + 5,
            )
            for index in range(1, 206)
        ]
        rows.extend(
            [(snapshot_date, 1000, "Kicker", "K", "TST", 1, 1.5, 1, 3)]
        )
        connection.executemany("insert into silver.int_ff_rankings__latest_redraft values (?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)


def make_store(tmp_path: Path, snapshot_date: date = date(2026, 9, 6)) -> RankingStore:
    analytics = tmp_path / "analytics.duckdb"
    write_analytics_database(analytics, snapshot_date)
    return RankingStore(tmp_path / "personal.duckdb", analytics, configure_minio=False)


def test_initialization_selects_200_offensive_players_and_freezes_snapshot(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.ensure_initialized()

    assert len(store.rankings()) == 200
    assert store.board_state()["source_snapshot_date"] == date(2026, 9, 6)
    assert all(row["pos"] in {"QB", "RB", "WR", "TE"} for row in store.rankings())

    write_analytics_database(store.analytics_database, date(2026, 9, 7))
    store.ensure_initialized()
    assert store.board_state()["source_snapshot_date"] == date(2026, 9, 6)

    store.reset_from_latest()
    assert store.board_state()["source_snapshot_date"] == date(2026, 9, 7)


def test_choice_is_idempotent_and_undo_restores_exact_state(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.ensure_initialized()
    matchup = store.matchup()
    before = {row["player_id"]: row for row in store.rankings()}

    assert store.complete_matchup(matchup.matchup_id, matchup.left.player_id)
    assert not store.complete_matchup(matchup.matchup_id, matchup.left.player_id)
    after = {row["player_id"]: row for row in store.rankings()}
    assert after[matchup.left.player_id]["personal_rating"] > before[matchup.left.player_id]["personal_rating"]
    assert after[matchup.left.player_id]["appearances"] == 1

    assert store.undo_last()
    restored = {row["player_id"]: row for row in store.rankings()}
    assert restored[matchup.left.player_id]["personal_rating"] == before[matchup.left.player_id]["personal_rating"]
    assert restored[matchup.right.player_id]["personal_rating"] == before[matchup.right.player_id]["personal_rating"]
    assert restored[matchup.left.player_id]["appearances"] == 0


def test_skip_counts_coverage_without_changing_ratings(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.ensure_initialized()
    matchup = store.matchup()

    assert store.complete_matchup(matchup.matchup_id, None)
    rows = {row["player_id"]: row for row in store.rankings()}

    assert rows[matchup.left.player_id]["personal_rating"] == matchup.left.personal_rating
    assert rows[matchup.right.player_id]["personal_rating"] == matchup.right.personal_rating
    assert rows[matchup.left.player_id]["appearances"] == 1
    assert rows[matchup.right.player_id]["appearances"] == 1


def test_export_contains_all_source_players_and_nullable_personal_values(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.ensure_initialized()

    rows = store.latest_rankings_with_personal()

    assert len(rows) == 206
    assert set(rows[0]) == {
        "snapshot_date",
        "player_id",
        "player",
        "pos",
        "team",
        "bye",
        "ecr",
        "best",
        "worst",
        "vs_ecr",
    }
    assert next(row for row in rows if row["pos"] == "K")["vs_ecr"] is None
