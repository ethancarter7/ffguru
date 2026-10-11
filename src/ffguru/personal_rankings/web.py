"""Defines the Flask routes for comparing players and viewing the personal board."""

import csv
import os
from io import StringIO
from pathlib import Path

from flask import Flask, Response, abort, flash, redirect, render_template, request, url_for

from ffguru.personal_rankings.analytics import AnalyticsStore, AnalyticsUnavailable
from ffguru.personal_rankings.store import BoardInitializationError, RankingStore

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIRECTORY = Path(os.environ.get("FFGURU_DATA_DIR", PROJECT_ROOT / "data"))


def format_metric(value: object, metric_key: str) -> str:
    if value is None:
        return "—"
    number = float(value)
    if metric_key in {"target_share", "opportunity_share", "fg_pct"}:
        return f"{number:.1%}"
    if metric_key in {
        "fantasy_points_ppr",
        "passing_epa",
        "rushing_epa",
        "receiving_epa",
        "passing_cpoe",
        "wopr",
    }:
        return f"{number:,.2f}"
    return f"{number:,.0f}" if number.is_integer() else f"{number:,.2f}"


def create_app(
    store: RankingStore | None = None,
    analytics_store: AnalyticsStore | None = None,
) -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("RANKINGS_SECRET_KEY", "local-rankings-secret")
    app.jinja_env.globals["format_metric"] = format_metric
    ranking_store = store or RankingStore(
        DATA_DIRECTORY / "personal_rankings.duckdb",
        DATA_DIRECTORY / "ffguru.duckdb",
    )
    player_analytics = analytics_store or AnalyticsStore(ranking_store.analytics_database)

    def initialize() -> Response | None:
        try:
            ranking_store.ensure_initialized()
        except BoardInitializationError as error:
            return Response(render_template("error.html", message=str(error)), status=503)
        return None

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/")
    def index() -> Response:
        return redirect(url_for("compare"))

    @app.get("/compare")
    def compare() -> str | Response:
        error = initialize()
        if error:
            return error
        return render_template(
            "compare.html",
            matchup=ranking_store.matchup(),
            progress=ranking_store.progress(),
            board=ranking_store.board_state(),
        )

    @app.post("/matchups/<matchup_id>/choose")
    def choose(matchup_id: str) -> Response:
        winner_id = request.form.get("winner_id", type=int)
        if winner_id is None or not ranking_store.complete_matchup(matchup_id, winner_id):
            flash("That matchup was already completed or is no longer valid.")
        return redirect(url_for("compare"))

    @app.post("/matchups/<matchup_id>/skip")
    def skip(matchup_id: str) -> Response:
        if not ranking_store.complete_matchup(matchup_id, None):
            flash("That matchup was already completed or is no longer valid.")
        return redirect(url_for("compare"))

    @app.post("/undo")
    def undo() -> Response:
        if ranking_store.undo_last():
            flash("Your last decision was undone.")
        else:
            flash("There is no completed decision to undo.")
        return redirect(url_for("compare"))

    @app.get("/rankings")
    def rankings() -> str | Response:
        error = initialize()
        if error:
            return error
        rows = ranking_store.rankings()
        sort_name = request.args.get("sort", "personal_rank")
        direction = request.args.get("direction", "asc")
        allowed_sorts = {
            "personal_rank",
            "player_id",
            "player",
            "pos",
            "team",
            "bye",
            "personal_rating",
            "ecr",
            "best",
            "worst",
            "movement_vs_ecr",
        }
        if sort_name not in allowed_sorts:
            sort_name = "personal_rank"
        reverse = direction == "desc"
        rows.sort(
            key=lambda row: (row[sort_name] is None, row[sort_name]),
            reverse=reverse,
        )
        return render_template(
            "rankings.html",
            rankings=rows,
            sort_name=sort_name,
            direction=direction,
            board=ranking_store.board_state(),
        )

    @app.get("/rankings.csv")
    def rankings_csv() -> Response:
        error = initialize()
        if error:
            return error
        fields = [
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
        ]
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(ranking_store.latest_rankings_with_personal())
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=latest_ff_rankings_with_personal.csv"
            },
        )

    @app.get("/analytics")
    def analytics() -> str | Response:
        position = request.args.get("position", "RB").upper()
        if position not in {"QB", "RB", "WR", "TE", "K"}:
            position = "RB"
        scope = request.args.get("scope", "week")
        if scope not in {"week", "season"}:
            scope = "week"
        try:
            context = player_analytics.context(
                season=request.args.get("season", type=int),
                season_type=request.args.get("season_type"),
                week=request.args.get("week", type=int),
            )
            selected_metric = player_analytics.metric(position, request.args.get("metric"))
            query = {
                "position": position,
                "season": context["season"],
                "season_type": context["season_type"],
                "week": context["week"],
            }
            weekly_ppr = player_analytics.leaders(**query, scope="week")
            season_ppr = player_analytics.leaders(**query, scope="season")
            metric_leaders = player_analytics.leaders(
                **query,
                metric=selected_metric,
                scope=scope,
                limit=20,
            )
        except AnalyticsUnavailable as error:
            return Response(render_template("error.html", message=str(error)), status=503)
        return render_template(
            "analytics.html",
            context=context,
            positions=("QB", "RB", "WR", "TE", "K"),
            position=position,
            metrics=player_analytics.metrics(position),
            selected_metric=selected_metric,
            scope=scope,
            weekly_ppr=weekly_ppr,
            season_ppr=season_ppr,
            metric_leaders=metric_leaders,
        )

    @app.get("/analytics/players/<player_id>")
    def analytics_player(player_id: str) -> str | Response:
        try:
            context = player_analytics.context(
                season=request.args.get("season", type=int),
                season_type=request.args.get("season_type"),
                week=request.args.get("week", type=int),
            )
            player = player_analytics.player(
                player_id,
                season=context["season"],
                season_type=context["season_type"],
                week=context["week"],
            )
        except AnalyticsUnavailable as error:
            return Response(render_template("error.html", message=str(error)), status=503)
        if player is None:
            abort(404)
        return render_template("analytics_player.html", context=context, player=player)

    @app.route("/reset", methods=["GET", "POST"])
    def reset() -> str | Response:
        if request.method == "POST":
            try:
                snapshot_date = ranking_store.reset_from_latest()
            except BoardInitializationError as error:
                flash(str(error))
                return redirect(url_for("reset"))
            flash(f"The board was reset from the {snapshot_date} snapshot.")
            return redirect(url_for("compare"))
        return render_template("reset.html")

    return app


def main() -> None:
    create_app().run(host="0.0.0.0", port=5000, debug=False, threaded=False)


if __name__ == "__main__":
    main()
