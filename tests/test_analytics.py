"""Tests gold-mart analytics queries and their Flask pages."""

from datetime import date
from pathlib import Path

import duckdb

from ffguru.personal_rankings.analytics import AnalyticsStore
from ffguru.personal_rankings.store import RankingStore
from ffguru.personal_rankings.web import create_app


def write_gold_analytics(path: Path) -> None:
    with duckdb.connect(str(path)) as connection:
        connection.execute("create schema gold")
        connection.execute(
            """
            create table gold.fct_player_week_stats (
                snapshot_date date, player_id varchar, player_display_name varchar,
                position varchar, headshot_url varchar, season integer, week integer,
                season_type varchar, team varchar
            )
            """
        )
        connection.execute(
            """
            insert into gold.fct_player_week_stats values
                ('2026-10-06', 'rb-1', 'Alpha Runner', 'RB', 'https://example.com/alpha.png', 2026, 1, 'REG', 'AAA'),
                ('2026-10-06', 'rb-1', 'Alpha Runner', 'RB', 'https://example.com/alpha.png', 2026, 2, 'REG', 'AAA'),
                ('2026-10-06', 'rb-2', 'Beta Runner', 'RB', null, 2026, 1, 'REG', 'BBB'),
                ('2026-10-06', 'rb-2', 'Beta Runner', 'RB', null, 2026, 2, 'REG', 'BBB')
            """
        )
        connection.execute(
            """
            create table gold.mart_rb_week_rankings (
                snapshot_date date, player_id varchar, player_display_name varchar,
                position varchar, headshot_url varchar, season integer, week integer,
                season_type varchar, game_id varchar, team varchar, opponent_team varchar,
                played_this_week boolean, season_to_date_games_played integer,
                fantasy_points_ppr double, fantasy_points_ppr_week_rank integer,
                season_to_date_fantasy_points_ppr double,
                season_to_date_fantasy_points_ppr_rank integer,
                opportunities double, opportunities_week_rank integer,
                season_to_date_opportunities double,
                season_to_date_opportunities_rank integer,
                opportunity_share double, opportunity_share_week_rank integer,
                season_to_date_opportunity_share double,
                season_to_date_opportunity_share_rank integer,
                rushing_yards double, receiving_yards double
            )
            """
        )
        connection.execute(
            """
            insert into gold.mart_rb_week_rankings values
                ('2026-10-06', 'rb-1', 'Alpha Runner', 'RB', 'https://example.com/alpha.png', 2026, 1, 'REG',
                 'g1', 'AAA', 'BBB', true, 1, 18, 1, 18, 1, 20, 1, 20, 1,
                 0.70, 1, 0.70, 1, 90, 30),
                ('2026-10-06', 'rb-1', 'Alpha Runner', 'RB', 'https://example.com/alpha.png', 2026, 2, 'REG',
                 'g2', 'AAA', 'CCC', true, 2, 12, 2, 30, 1, 15, 2, 35, 1,
                 0.55, 2, 0.625, 1, 55, 25),
                ('2026-10-06', 'rb-2', 'Beta Runner', 'RB', null, 2026, 1, 'REG',
                 'g3', 'BBB', 'AAA', true, 1, 10, 2, 10, 2, 12, 2, 12, 2,
                 0.45, 2, 0.45, 2, 40, 35),
                ('2026-10-06', 'rb-2', 'Beta Runner', 'RB', null, 2026, 2, 'REG',
                 'g4', 'BBB', 'DDD', true, 2, 20, 1, 30, 1, 22, 1, 34, 2,
                 0.80, 1, 0.68, 1, 110, 20)
            """
        )


def test_analytics_store_uses_selected_week_and_cumulative_columns(tmp_path: Path) -> None:
    database = tmp_path / "analytics.duckdb"
    write_gold_analytics(database)
    store = AnalyticsStore(database)

    context = store.context()
    assert context["snapshot_date"] == date(2026, 10, 6)
    assert context["week"] == 2

    weekly = store.leaders(
        position="RB", season=2026, season_type="REG", week=2, scope="week"
    )
    season = store.leaders(
        position="RB", season=2026, season_type="REG", week=2, scope="season"
    )
    opportunity_share = store.metric("RB", "opportunity_share")
    usage = store.leaders(
        position="RB",
        season=2026,
        season_type="REG",
        week=2,
        metric=opportunity_share,
        scope="season",
    )

    assert weekly[0]["player_display_name"] == "Beta Runner"
    assert season[0]["metric_value"] == 30
    assert usage[0]["metric_value"] == 0.625


def test_analytics_dashboard_and_player_profile(tmp_path: Path) -> None:
    database = tmp_path / "analytics.duckdb"
    write_gold_analytics(database)
    ranking_store = RankingStore(
        tmp_path / "personal.duckdb", database, configure_minio=False
    )
    app = create_app(ranking_store, AnalyticsStore(database))
    app.config.update(TESTING=True)
    client = app.test_client()

    response = client.get(
        "/analytics?position=RB&week=2&metric=opportunity_share&scope=season"
    )
    assert response.status_code == 200
    assert b"Player analytics" in response.data
    assert b"Opportunity share" in response.data
    assert b"Alpha Runner" in response.data
    assert b'class="player-headshot"' in response.data
    assert b'class="player-headshot-fallback"' in response.data

    profile = client.get("/analytics/players/rb-1?season=2026&season_type=REG&week=2")
    assert profile.status_code == 200
    assert b"Weekly PPR trend" in profile.data
    assert b"Game log" in profile.data
    assert b"Alpha Runner" in profile.data
    assert client.get("/analytics/players/missing").status_code == 404
