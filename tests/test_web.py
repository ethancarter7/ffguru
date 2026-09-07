"""Tests the Flask comparison, ranking, CSV, reset, and health routes."""

from datetime import date

from ffguru.personal_rankings.store import RankingStore
from ffguru.personal_rankings.web import create_app
from tests.test_store import write_analytics_database


def test_web_workflow(tmp_path) -> None:
    analytics = tmp_path / "analytics.duckdb"
    write_analytics_database(analytics, date(2026, 9, 6))
    store = RankingStore(tmp_path / "personal.duckdb", analytics, configure_minio=False)
    app = create_app(store)
    app.config.update(TESTING=True)
    client = app.test_client()

    assert client.get("/health").status_code == 200
    response = client.get("/compare")
    assert response.status_code == 200
    assert b"Who would you draft?" in response.data

    matchup = store.matchup()
    response = client.post(
        f"/matchups/{matchup.matchup_id}/choose",
        data={"winner_id": matchup.left.player_id},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert store.progress()["completed_matchups"] == 1

    client.post(
        f"/matchups/{matchup.matchup_id}/choose",
        data={"winner_id": matchup.left.player_id},
    )
    assert store.progress()["completed_matchups"] == 1

    assert client.get("/rankings?sort=ecr&direction=desc").status_code == 200
    csv_response = client.get("/rankings.csv")
    assert csv_response.status_code == 200
    assert csv_response.headers["Content-Type"].startswith("text/csv")
    assert (
        b"snapshot_date,player_id,player,pos,team,bye,ecr,best,worst,vs_ecr"
        in csv_response.data
    )
    assert b"personal_rating" not in csv_response.data

    assert client.post("/undo", follow_redirects=True).status_code == 200
    assert store.progress()["completed_matchups"] == 0
    assert client.get("/reset").status_code == 200
    assert client.post("/reset", follow_redirects=True).status_code == 200
