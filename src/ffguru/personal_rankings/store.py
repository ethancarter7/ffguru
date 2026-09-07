"""Persists the frozen player board, matchups, and personal ratings in DuckDB."""

import os
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4

import duckdb

from ffguru.personal_rankings.ranking import (
    COVERAGE_TARGET,
    RankedPlayer,
    choose_pair,
    elo_ratings,
    initial_rating,
)


class BoardInitializationError(RuntimeError):
    pass


@dataclass(frozen=True)
class Player:
    player_id: int
    player: str
    pos: str
    team: str | None
    bye: int | None
    ecr: float
    best: int | None
    worst: int | None
    personal_rating: float
    appearances: int


@dataclass(frozen=True)
class Matchup:
    matchup_id: str
    left: Player
    right: Player


class RankingStore:
    def __init__(
        self,
        personal_database: str | Path,
        analytics_database: str | Path,
        *,
        configure_minio: bool = True,
    ) -> None:
        self.personal_database = Path(personal_database)
        self.analytics_database = Path(analytics_database)
        self.configure_minio = configure_minio
        self.personal_database.parent.mkdir(parents=True, exist_ok=True)
        self._create_schema()

    def _connect(self) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(str(self.personal_database))

    def _create_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                create table if not exists board_state (
                    board_id integer primary key check (board_id = 1),
                    source_snapshot_date date not null,
                    created_at timestamptz not null
                );

                create table if not exists board_players (
                    player_id bigint primary key,
                    player varchar not null,
                    pos varchar not null,
                    team varchar,
                    bye integer,
                    ecr double not null,
                    best integer,
                    worst integer,
                    personal_rating double not null,
                    appearances integer not null default 0
                );

                create table if not exists matchups (
                    matchup_id varchar primary key,
                    created_at timestamptz not null,
                    completed_at timestamptz,
                    left_player_id bigint not null,
                    right_player_id bigint not null,
                    winner_player_id bigint,
                    outcome varchar,
                    left_rating_before double not null,
                    right_rating_before double not null,
                    left_appearances_before integer not null,
                    right_appearances_before integer not null,
                    undone boolean not null default false
                )
                """
            )

    def ensure_initialized(self) -> None:
        with self._connect() as connection:
            initialized = connection.execute("select count(*) from board_state").fetchone()[0]
        if not initialized:
            self.reset_from_latest()

    def _configure_source(self, connection: duckdb.DuckDBPyConnection) -> None:
        if not self.configure_minio:
            return
        connection.load_extension("httpfs")
        connection.execute(
            """
            create or replace secret rankings_app_minio (
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
                os.environ.get("MINIO_ACCESS_KEY", "minioadmin"),
                os.environ.get("MINIO_SECRET_KEY", "minioadmin"),
                os.environ.get("MINIO_DUCKDB_ENDPOINT", "minio:9000"),
            ],
        )

    def _load_latest_players(self) -> tuple[date, list[tuple]]:
        try:
            with duckdb.connect(str(self.analytics_database), read_only=True) as connection:
                self._configure_source(connection)
                rows = connection.execute(
                    """
                    select snapshot_date, player_id, player, pos, team, bye, ecr, best, worst
                    from silver.int_ff_rankings__latest_redraft
                    where pos in ('QB', 'RB', 'WR', 'TE')
                    order by ecr, player_id
                    limit 200
                    """
                ).fetchall()
        except duckdb.Error as error:
            raise BoardInitializationError(
                "The latest rankings could not be read. If dbt is running, wait for it to finish and retry."
            ) from error

        if len(rows) != 200:
            raise BoardInitializationError(
                f"Expected 200 offensive players in the latest rankings but found {len(rows)}."
            )
        snapshot_dates = {row[0] for row in rows}
        if len(snapshot_dates) != 1:
            raise BoardInitializationError("The source rankings contain more than one snapshot date.")
        return snapshot_dates.pop(), rows

    def latest_rankings_with_personal(self) -> list[dict[str, object]]:
        try:
            with duckdb.connect(str(self.analytics_database), read_only=True) as connection:
                self._configure_source(connection)
                rows = connection.execute(
                    """
                    select snapshot_date, player_id, player, pos, team, bye, ecr, best, worst
                    from silver.int_ff_rankings__latest_redraft
                    order by ecr, player_id
                    """
                ).fetchall()
        except duckdb.Error as error:
            raise BoardInitializationError(
                "The latest rankings could not be read. If dbt is running, wait for it to finish and retry."
            ) from error

        personal_ranks = {
            row["player_id"]: row["personal_rank"]
            for row in self.rankings()
        }
        fields = (
            "snapshot_date",
            "player_id",
            "player",
            "pos",
            "team",
            "bye",
            "ecr",
            "best",
            "worst",
        )
        results = []
        for row in rows:
            result = dict(zip(fields, row, strict=True))
            personal_rank = personal_ranks.get(result["player_id"])
            result["vs_ecr"] = (
                round(result["ecr"] - personal_rank, 2)
                if personal_rank is not None
                else None
            )
            results.append(result)
        return results

    def reset_from_latest(self) -> date:
        snapshot_date, rows = self._load_latest_players()
        now = datetime.now(UTC)
        with self._connect() as connection:
            connection.begin()
            try:
                connection.execute("delete from matchups")
                connection.execute("delete from board_players")
                connection.execute("delete from board_state")
                connection.executemany(
                    """
                    insert into board_players values (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                    """,
                    [
                        (
                            row[1],
                            row[2],
                            row[3],
                            row[4],
                            row[5],
                            row[6],
                            row[7],
                            row[8],
                            initial_rating(row[6]),
                        )
                        for row in rows
                    ],
                )
                connection.execute(
                    "insert into board_state values (1, ?, ?)",
                    [snapshot_date, now],
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        return snapshot_date

    @staticmethod
    def _player(row: tuple) -> Player:
        return Player(*row)

    def board_state(self) -> dict[str, object]:
        with self._connect() as connection:
            row = connection.execute(
                "select source_snapshot_date, created_at from board_state where board_id = 1"
            ).fetchone()
        return {"source_snapshot_date": row[0], "created_at": row[1]}

    def rankings(self) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                select player_id, player, pos, team, bye, ecr, best, worst,
                       personal_rating, appearances
                from board_players
                order by personal_rating desc, ecr, player_id
                """
            ).fetchall()
        results = []
        for personal_rank, row in enumerate(rows, start=1):
            player = self._player(row)
            result = asdict(player)
            result["personal_rank"] = personal_rank
            result["movement_vs_ecr"] = round(player.ecr - personal_rank, 2)
            results.append(result)
        return results

    def progress(self) -> dict[str, int | float | bool]:
        with self._connect() as connection:
            total, covered, appearances = connection.execute(
                """
                select count(*),
                       count(*) filter (where appearances >= ?),
                       sum(least(appearances, ?))
                from board_players
                """,
                [COVERAGE_TARGET, COVERAGE_TARGET],
            ).fetchone()
            completed = connection.execute(
                "select count(*) from matchups where outcome is not null and not undone"
            ).fetchone()[0]
        target_appearances = total * COVERAGE_TARGET
        return {
            "total_players": total,
            "covered_players": covered,
            "completed_matchups": completed,
            "target_appearances": target_appearances,
            "progress_percent": round(100.0 * appearances / target_appearances, 1),
            "complete": covered == total,
        }

    def _pending_matchup(self, connection: duckdb.DuckDBPyConnection) -> tuple | None:
        return connection.execute(
            """
            select matchup_id, left_player_id, right_player_id
            from matchups
            where outcome is null and not undone
            order by created_at desc
            limit 1
            """
        ).fetchone()

    def _players_by_id(
        self, connection: duckdb.DuckDBPyConnection, player_ids: tuple[int, int]
    ) -> dict[int, Player]:
        placeholders = ", ".join("?" for _ in player_ids)
        rows = connection.execute(
            f"""
            select player_id, player, pos, team, bye, ecr, best, worst,
                   personal_rating, appearances
            from board_players
            where player_id in ({placeholders})
            """,
            list(player_ids),
        ).fetchall()
        return {row[0]: self._player(row) for row in rows}

    def matchup(self) -> Matchup:
        with self._connect() as connection:
            pending = self._pending_matchup(connection)
            if pending is None:
                player_rows = connection.execute(
                    "select player_id, personal_rating, ecr, appearances from board_players"
                ).fetchall()
                players = [RankedPlayer(*row) for row in player_rows]
                pair_rows = connection.execute(
                    """
                    select left_player_id, right_player_id, count(*)
                    from matchups
                    where outcome is not null and not undone
                    group by left_player_id, right_player_id
                    """
                ).fetchall()
                pair_counts: dict[frozenset[int], int] = {}
                for left_id, right_id, count in pair_rows:
                    pair = frozenset((left_id, right_id))
                    pair_counts[pair] = pair_counts.get(pair, 0) + count
                last = connection.execute(
                    """
                    select left_player_id, right_player_id
                    from matchups
                    where outcome is not null and not undone
                    order by completed_at desc, matchup_id desc
                    limit 1
                    """
                ).fetchone()
                last_pair = frozenset(last) if last else None
                completed_count = sum(pair_counts.values())
                left_id, right_id = choose_pair(
                    players, pair_counts, last_pair, completed_count
                )
                selected = self._players_by_id(connection, (left_id, right_id))
                matchup_id = str(uuid4())
                connection.execute(
                    """
                    insert into matchups (
                        matchup_id, created_at, left_player_id, right_player_id,
                        left_rating_before, right_rating_before,
                        left_appearances_before, right_appearances_before
                    ) values (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        matchup_id,
                        datetime.now(UTC),
                        left_id,
                        right_id,
                        selected[left_id].personal_rating,
                        selected[right_id].personal_rating,
                        selected[left_id].appearances,
                        selected[right_id].appearances,
                    ],
                )
                pending = (matchup_id, left_id, right_id)

            selected = self._players_by_id(connection, (pending[1], pending[2]))
            return Matchup(pending[0], selected[pending[1]], selected[pending[2]])

    def complete_matchup(self, matchup_id: str, winner_id: int | None) -> bool:
        with self._connect() as connection:
            connection.begin()
            row = connection.execute(
                """
                select left_player_id, right_player_id, outcome,
                       left_rating_before, right_rating_before,
                       left_appearances_before, right_appearances_before
                from matchups where matchup_id = ?
                """,
                [matchup_id],
            ).fetchone()
            if row is None or row[2] is not None:
                connection.rollback()
                return False

            left_id, right_id = row[0], row[1]
            if winner_id is not None and winner_id not in (left_id, right_id):
                connection.rollback()
                return False

            left_rating, right_rating = row[3], row[4]
            outcome = "skip"
            if winner_id is not None:
                outcome = "left" if winner_id == left_id else "right"
                if winner_id == left_id:
                    left_rating, right_rating = elo_ratings(left_rating, right_rating)
                else:
                    right_rating, left_rating = elo_ratings(right_rating, left_rating)

            connection.execute(
                "update board_players set personal_rating = ?, appearances = ? where player_id = ?",
                [left_rating, row[5] + 1, left_id],
            )
            connection.execute(
                "update board_players set personal_rating = ?, appearances = ? where player_id = ?",
                [right_rating, row[6] + 1, right_id],
            )
            connection.execute(
                """
                update matchups
                set completed_at = ?, winner_player_id = ?, outcome = ?
                where matchup_id = ?
                """,
                [datetime.now(UTC), winner_id, outcome, matchup_id],
            )
            connection.commit()
            return True

    def undo_last(self) -> bool:
        with self._connect() as connection:
            connection.begin()
            connection.execute("delete from matchups where outcome is null")
            row = connection.execute(
                """
                select matchup_id, left_player_id, right_player_id,
                       left_rating_before, right_rating_before,
                       left_appearances_before, right_appearances_before
                from matchups
                where outcome is not null and not undone
                order by completed_at desc, matchup_id desc
                limit 1
                """
            ).fetchone()
            if row is None:
                connection.rollback()
                return False
            connection.execute(
                "update board_players set personal_rating = ?, appearances = ? where player_id = ?",
                [row[3], row[5], row[1]],
            )
            connection.execute(
                "update board_players set personal_rating = ?, appearances = ? where player_id = ?",
                [row[4], row[6], row[2]],
            )
            connection.execute(
                "update matchups set undone = true where matchup_id = ?",
                [row[0]],
            )
            connection.commit()
            return True
