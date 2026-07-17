"""Pull player game logs from the NBA stats API and cache them locally.

The Streamlit app never calls the API at runtime; it reads the committed
snapshot in data/. stats.nba.com blocks most cloud IPs, so the refresh runs
from a residential machine (scripts/refresh_data.py) and the snapshot ships
with the repo.
"""
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SNAPSHOT = DATA_DIR / "player_game_logs.parquet"
COLUMNS = ["player_id", "player_name", "team", "game_date", "minutes"]


def normalize_games(raw: pd.DataFrame) -> pd.DataFrame:
    """nba_api LeagueGameLog player rows -> the engine's input schema."""
    out = pd.DataFrame({
        "player_id": raw["PLAYER_ID"],
        "player_name": raw["PLAYER_NAME"],
        "team": raw["TEAM_ABBREVIATION"],
        "game_date": pd.to_datetime(raw["GAME_DATE"]),
        "minutes": pd.to_numeric(raw["MIN"], errors="coerce"),
    })
    out = out[out["minutes"] > 0]
    return out.reset_index(drop=True)


def fetch_season(season: str, season_type: str = "Regular Season") -> pd.DataFrame:
    """One API call returns every player-game row for a season."""
    from nba_api.stats.endpoints import leaguegamelog

    log = leaguegamelog.LeagueGameLog(
        season=season,
        player_or_team_abbreviation="P",
        season_type_all_star=season_type,
        timeout=90,
    )
    return normalize_games(log.get_data_frames()[0])


def save_snapshot(games: pd.DataFrame, season: str) -> Path:
    DATA_DIR.mkdir(exist_ok=True)
    games = games.copy()
    games["season"] = season
    games.to_parquet(SNAPSHOT, index=False)
    return SNAPSHOT


def load_snapshot() -> pd.DataFrame:
    return pd.read_parquet(SNAPSHOT)
