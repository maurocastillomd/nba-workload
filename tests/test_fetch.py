"""Tests for the game-log normalizer (the pure part of the fetch layer)."""
import pandas as pd

from nba_workload.fetch import normalize_games


def test_normalize_maps_nba_api_columns_and_types():
    raw = pd.DataFrame({
        "PLAYER_ID": [203999, 1629029],
        "PLAYER_NAME": ["Nikola Jokic", "Luka Doncic"],
        "TEAM_ABBREVIATION": ["DEN", "LAL"],
        "GAME_DATE": ["2026-01-15", "2026-01-15"],
        "MIN": [36, 38],
        "FGA": [20, 25],  # extra columns must be dropped
    })
    out = normalize_games(raw)
    assert list(out.columns) == ["player_id", "player_name", "team", "game_date", "minutes"]
    assert pd.api.types.is_datetime64_any_dtype(out["game_date"])
    assert out["minutes"].tolist() == [36.0, 38.0]


def test_normalize_drops_rows_without_minutes():
    raw = pd.DataFrame({
        "PLAYER_ID": [1, 2],
        "PLAYER_NAME": ["A", "B"],
        "TEAM_ABBREVIATION": ["ORL", "MIA"],
        "GAME_DATE": ["2026-01-15", "2026-01-15"],
        "MIN": [None, 0],
    })
    out = normalize_games(raw)
    assert len(out) == 0
