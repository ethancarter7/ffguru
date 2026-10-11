"""Reads the gold player-ranking marts for the analytics pages."""

from dataclasses import dataclass
from pathlib import Path

import duckdb


class AnalyticsUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class Metric:
    key: str
    label: str
    season_key: str | None = None

    @property
    def cumulative_key(self) -> str:
        return self.season_key or f"season_to_date_{self.key}"


COMMON_PPR = Metric("fantasy_points_ppr", "PPR points")

POSITION_METRICS = {
    "QB": (
        COMMON_PPR,
        Metric("completions", "Completions"),
        Metric("attempts", "Pass attempts"),
        Metric("passing_yards", "Passing yards"),
        Metric("passing_tds", "Passing touchdowns"),
        Metric("passing_interceptions", "Interceptions"),
        Metric("sacks_suffered", "Sacks suffered"),
        Metric("passing_air_yards", "Passing air yards"),
        Metric("passing_first_downs", "Passing first downs"),
        Metric("passing_epa", "Passing EPA"),
        Metric("passing_cpoe", "Passing CPOE"),
        Metric("carries", "Carries"),
        Metric("rushing_yards", "Rushing yards"),
        Metric("rushing_tds", "Rushing touchdowns"),
        Metric("rushing_epa", "Rushing EPA"),
    ),
    "RB": (
        COMMON_PPR,
        Metric("opportunities", "Opportunities"),
        Metric("opportunity_share", "Opportunity share"),
        Metric("carries", "Carries"),
        Metric("rushing_yards", "Rushing yards"),
        Metric("rushing_tds", "Rushing touchdowns"),
        Metric("rushing_first_downs", "Rushing first downs"),
        Metric("rushing_epa", "Rushing EPA"),
        Metric("targets", "Targets"),
        Metric("receptions", "Receptions"),
        Metric("receiving_yards", "Receiving yards"),
        Metric("receiving_tds", "Receiving touchdowns"),
        Metric("receiving_air_yards", "Receiving air yards"),
        Metric("receiving_yards_after_catch", "Yards after catch"),
        Metric("receiving_epa", "Receiving EPA"),
        Metric("target_share", "Target share", "season_to_date_avg_target_share"),
        Metric("wopr", "WOPR", "season_to_date_avg_wopr"),
    ),
    "WR": (
        COMMON_PPR,
        Metric("targets", "Targets"),
        Metric("receptions", "Receptions"),
        Metric("receiving_yards", "Receiving yards"),
        Metric("receiving_tds", "Receiving touchdowns"),
        Metric("receiving_air_yards", "Receiving air yards"),
        Metric("receiving_yards_after_catch", "Yards after catch"),
        Metric("receiving_first_downs", "Receiving first downs"),
        Metric("receiving_epa", "Receiving EPA"),
        Metric("target_share", "Target share", "season_to_date_avg_target_share"),
        Metric("wopr", "WOPR", "season_to_date_avg_wopr"),
        Metric("carries", "Carries"),
        Metric("rushing_yards", "Rushing yards"),
        Metric("rushing_tds", "Rushing touchdowns"),
    ),
    "TE": (
        COMMON_PPR,
        Metric("targets", "Targets"),
        Metric("receptions", "Receptions"),
        Metric("receiving_yards", "Receiving yards"),
        Metric("receiving_tds", "Receiving touchdowns"),
        Metric("receiving_air_yards", "Receiving air yards"),
        Metric("receiving_yards_after_catch", "Yards after catch"),
        Metric("receiving_first_downs", "Receiving first downs"),
        Metric("receiving_epa", "Receiving EPA"),
        Metric("target_share", "Target share", "season_to_date_avg_target_share"),
        Metric("wopr", "WOPR", "season_to_date_avg_wopr"),
        Metric("carries", "Carries"),
        Metric("rushing_yards", "Rushing yards"),
        Metric("rushing_tds", "Rushing touchdowns"),
    ),
    "K": (
        COMMON_PPR,
        Metric("fg_made", "Field goals made"),
        Metric("fg_att", "Field-goal attempts"),
        Metric("fg_missed", "Field goals missed"),
        Metric("fg_blocked", "Field goals blocked"),
        Metric("fg_long", "Longest field goal"),
        Metric("fg_pct", "Field-goal percentage"),
    ),
}

POSITION_TABLES = {
    position: f"gold.mart_{position.lower()}_week_rankings" for position in POSITION_METRICS
}

DEFAULT_METRICS = {
    "QB": "passing_yards",
    "RB": "opportunity_share",
    "WR": "target_share",
    "TE": "target_share",
    "K": "fg_made",
}

PROFILE_METRICS = {
    "QB": ("passing_yards", "passing_tds", "rushing_yards"),
    "RB": ("opportunities", "opportunity_share", "rushing_yards", "receiving_yards"),
    "WR": ("targets", "target_share", "receiving_yards", "receiving_tds"),
    "TE": ("targets", "target_share", "receiving_yards", "receiving_tds"),
    "K": ("fg_made", "fg_att", "fg_pct"),
}


class AnalyticsStore:
    def __init__(self, analytics_database: str | Path) -> None:
        self.analytics_database = Path(analytics_database)

    def _fetchall(self, query: str, parameters: list[object] | None = None) -> list[dict]:
        try:
            with duckdb.connect(str(self.analytics_database), read_only=True) as connection:
                result = connection.execute(query, parameters or [])
                columns = [column[0] for column in result.description]
                return [dict(zip(columns, row, strict=True)) for row in result.fetchall()]
        except duckdb.Error as error:
            raise AnalyticsUnavailable(
                "Analytics are temporarily unavailable. Close DuckDB UI or wait for dbt to finish, "
                "then retry."
            ) from error

    def context(
        self,
        *,
        season: int | None = None,
        season_type: str | None = None,
        week: int | None = None,
    ) -> dict[str, object]:
        rows = self._fetchall(
            """
            select distinct snapshot_date, season, season_type, week
            from gold.fct_player_week_stats
            order by season desc, season_type, week desc
            """
        )
        if not rows:
            raise AnalyticsUnavailable("No player analytics are available yet.")

        seasons = sorted({row["season"] for row in rows}, reverse=True)
        selected_season = season if season in seasons else seasons[0]
        season_types = sorted(
            {row["season_type"] for row in rows if row["season"] == selected_season}
        )
        preferred_type = "REG" if "REG" in season_types else season_types[0]
        selected_type = season_type if season_type in season_types else preferred_type
        weeks = sorted(
            {
                row["week"]
                for row in rows
                if row["season"] == selected_season and row["season_type"] == selected_type
            }
        )
        selected_week = week if week in weeks else weeks[-1]
        return {
            "snapshot_date": max(row["snapshot_date"] for row in rows),
            "seasons": seasons,
            "season_types": season_types,
            "weeks": weeks,
            "latest_week": weeks[-1],
            "season": selected_season,
            "season_type": selected_type,
            "week": selected_week,
        }

    @staticmethod
    def metrics(position: str) -> tuple[Metric, ...]:
        return POSITION_METRICS[position]

    @staticmethod
    def metric(position: str, metric_key: str | None) -> Metric:
        metrics = {metric.key: metric for metric in POSITION_METRICS[position]}
        return metrics.get(metric_key or "", metrics[DEFAULT_METRICS[position]])

    def leaders(
        self,
        *,
        position: str,
        season: int,
        season_type: str,
        week: int,
        metric: Metric = COMMON_PPR,
        scope: str = "week",
        limit: int = 10,
    ) -> list[dict]:
        table = POSITION_TABLES[position]
        if scope == "season":
            value_column = metric.cumulative_key
            rank_column = f"{value_column}_rank"
            eligibility = "season_to_date_games_played > 0"
        else:
            value_column = metric.key
            rank_column = f"{metric.key}_week_rank"
            eligibility = "played_this_week"
        return self._fetchall(
            f"""
            select player_id, player_display_name, team, headshot_url,
                   {value_column} as metric_value, {rank_column} as metric_rank
            from {table}
            where season = ? and season_type = ? and week = ?
              and {eligibility} and {rank_column} is not null
            order by {rank_column}, player_display_name, player_id
            limit ?
            """,
            [season, season_type, week, limit],
        )

    def player(
        self,
        player_id: str,
        *,
        season: int,
        season_type: str,
        week: int,
    ) -> dict | None:
        identity_rows = self._fetchall(
            """
            select player_id, player_display_name, position, headshot_url, team
            from gold.fct_player_week_stats
            where cast(player_id as varchar) = ? and season = ? and season_type = ? and week <= ?
            order by week desc
            limit 1
            """,
            [player_id, season, season_type, week],
        )
        if not identity_rows:
            return None

        player = identity_rows[0]
        position = player["position"]
        if position not in POSITION_TABLES:
            return None
        profile_metrics = PROFILE_METRICS[position]
        metric_columns = ", ".join(profile_metrics)
        rows = self._fetchall(
            f"""
            select week, team, opponent_team, played_this_week,
                   fantasy_points_ppr, fantasy_points_ppr_week_rank,
                   season_to_date_fantasy_points_ppr,
                   season_to_date_fantasy_points_ppr_rank,
                   {metric_columns}
            from {POSITION_TABLES[position]}
            where cast(player_id as varchar) = ? and season = ? and season_type = ? and week <= ?
            order by week
            """,
            [player_id, season, season_type, week],
        )
        if not rows:
            return None

        max_ppr = max((max(row["fantasy_points_ppr"] or 0, 0) for row in rows), default=0)
        for row in rows:
            row["trend_percent"] = (
                round(max(row["fantasy_points_ppr"] or 0, 0) / max_ppr * 100, 1)
                if max_ppr
                else 0
            )
        player["game_log"] = rows
        player["latest"] = rows[-1]
        player["profile_metrics"] = [
            next(metric for metric in POSITION_METRICS[position] if metric.key == key)
            for key in profile_metrics
        ]
        return player
