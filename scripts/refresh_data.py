"""Refresh the data snapshot from the NBA stats API.

Run from a residential machine (stats.nba.com blocks most cloud IPs):

    .venv/bin/python scripts/refresh_data.py [SEASON]

Then commit data/player_game_logs.parquet and push; Streamlit Cloud redeploys.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nba_workload.fetch import fetch_season, save_snapshot

DEFAULT_SEASON = "2025-26"


def main():
    season = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SEASON
    print(f"Fetching {season} player game logs from stats.nba.com ...")
    games = fetch_season(season)
    path = save_snapshot(games, season)
    print(
        f"Saved {len(games):,} player-game rows "
        f"({games['player_id'].nunique()} players, "
        f"{games['game_date'].min():%Y-%m-%d} to {games['game_date'].max():%Y-%m-%d}) "
        f"-> {path}"
    )


if __name__ == "__main__":
    main()
