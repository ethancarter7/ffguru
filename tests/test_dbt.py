"""Tests construction of dbt build subprocess commands."""

from ffguru.tasks.transformation import dbt


def test_build_dbt_project_builds_everything_by_default(monkeypatch, tmp_path):
    calls = []
    monkeypatch.delenv("DBT_PROFILES_DIR", raising=False)
    monkeypatch.setattr(dbt.subprocess, "run", lambda command, check: calls.append((command, check)))

    dbt.build_dbt_project(project_dir=tmp_path)

    assert calls == [
        (
            [
                "dbt",
                "build",
                "--project-dir",
                str(tmp_path),
                "--profiles-dir",
                str(tmp_path),
            ],
            True,
        )
    ]


def test_build_dbt_project_adds_selector(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setenv("DBT_PROFILES_DIR", "/profiles")
    monkeypatch.setattr(dbt.subprocess, "run", lambda command, check: calls.append((command, check)))

    dbt.build_dbt_project(project_dir=tmp_path, select="+int_player_stats__latest")

    assert calls == [
        (
            [
                "dbt",
                "build",
                "--project-dir",
                str(tmp_path),
                "--profiles-dir",
                "/profiles",
                "--select",
                "+int_player_stats__latest",
            ],
            True,
        )
    ]
