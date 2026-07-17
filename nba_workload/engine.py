"""Deterministic workload engine.

Input: one row per player-game (player_id, player_name, team, game_date, minutes).
Output: one row per player-day with trailing-window metrics and a transparent
point-based flag. No model writes a number here; everything is arithmetic on
public box-score minutes.
"""
import numpy as np
import pandas as pd

from . import config


def _game_minutes_z(day_minutes: pd.Series) -> pd.Series:
    """z-score of each game's minutes vs the player's own prior 28 days of games.

    day_minutes: daily-indexed minutes (0 on off days). Returns a daily series,
    NaN on off days and on games without enough individual history.
    """
    z = pd.Series(np.nan, index=day_minutes.index)
    game_days = day_minutes[day_minutes > 0]
    for date, minutes in game_days.items():
        window_start = date - pd.Timedelta(days=config.CHRONIC_DAYS)
        prior = game_days[(game_days.index >= window_start) & (game_days.index < date)]
        if len(prior) < config.MIN_PRIOR_GAMES_FOR_Z:
            continue
        std = max(prior.std(), config.Z_STD_FLOOR)
        z[date] = (minutes - prior.mean()) / std
    return z


def _flag(df: pd.DataFrame) -> pd.DataFrame:
    """Point-based flag. Each rule is one published threshold in config."""
    rated = df["chronic_daily"] >= config.CHRONIC_FLOOR_DAILY
    acwr_red = rated & (df["acwr"] >= config.ACWR_RED)
    acwr_amber = rated & (df["acwr"] >= config.ACWR_AMBER) & ~acwr_red
    low_chronic = ~rated & (df["acute_7d"] >= config.LOW_CHRONIC_ACUTE_MIN)
    dense = df["games_7d"] >= config.GAMES_7D_HIGH
    b2b = df["b2b"]
    spike = df["spike_z_7d"] >= config.MIN_Z_SPIKE

    points = (
        2 * acwr_red.astype(int)
        + acwr_amber.astype(int)
        + 2 * low_chronic.astype(int)
        + dense.astype(int)
        + b2b.astype(int)
        + spike.astype(int)
    )

    reasons = []
    for i in range(len(df)):
        r = []
        if acwr_red.iat[i]:
            r.append(f"ACWR {df['acwr'].iat[i]:.2f} ≥ {config.ACWR_RED}")
        elif acwr_amber.iat[i]:
            r.append(f"ACWR {df['acwr'].iat[i]:.2f} ≥ {config.ACWR_AMBER}")
        if low_chronic.iat[i]:
            r.append(
                f"low-chronic ramp-up ({df['acute_7d'].iat[i]:.0f} min this week on a minimal 28-day base)"
            )
        if dense.iat[i]:
            r.append(f"{int(df['games_7d'].iat[i])} games in 7 days")
        if b2b.iat[i]:
            r.append("back-to-back")
        if spike.iat[i]:
            r.append(f"minutes spike vs own baseline (z={df['spike_z_7d'].iat[i]:.1f})")
        reasons.append("; ".join(r))

    df = df.copy()
    df["risk_points"] = points
    df["reasons"] = reasons
    df["state"] = np.where(
        points >= config.RED_POINTS, "RED",
        np.where(points >= config.AMBER_POINTS, "AMBER", "GREEN"),
    )
    return df


def compute_daily_metrics(
    games: pd.DataFrame,
    season_end: pd.Timestamp | str | None = None,
) -> pd.DataFrame:
    """Expand game logs into a per-player daily grid with trailing metrics.

    games columns: player_id, player_name, team, game_date, minutes.
    Each player's grid runs from their first game to season_end (default:
    the latest game date in the data plus one acute window, so trailing
    windows can be read as they decay after a player's last appearance).
    """
    games = games.copy()
    games["game_date"] = pd.to_datetime(games["game_date"])
    if season_end is not None:
        end = pd.Timestamp(season_end)
    else:
        end = games["game_date"].max() + pd.Timedelta(days=config.ACUTE_DAYS)

    frames = []
    for player_id, g in games.groupby("player_id"):
        g = g.sort_values("game_date")
        idx = pd.date_range(g["game_date"].min(), end, freq="D")
        day_minutes = g.groupby("game_date")["minutes"].sum().reindex(idx, fill_value=0.0)
        played = day_minutes > 0

        df = pd.DataFrame({
            "player_id": player_id,
            "player_name": g["player_name"].iloc[-1],
            "team": g["team"].iloc[-1],
            "date": idx,
            "minutes": day_minutes.values,
            "played": played.values,
        })
        df["acute_7d"] = day_minutes.rolling(config.ACUTE_DAYS, min_periods=1).sum().values
        # fixed 28-day denominator: average daily load over the window, zeros included
        df["chronic_daily"] = (
            day_minutes.rolling(config.CHRONIC_DAYS, min_periods=1).sum().values
            / config.CHRONIC_DAYS
        )
        df["games_7d"] = (
            played.astype(int).rolling(config.ACUTE_DAYS, min_periods=1).sum().values
        )
        df["acwr"] = np.where(
            df["chronic_daily"] >= config.CHRONIC_FLOOR_DAILY,
            (df["acute_7d"] / config.ACUTE_DAYS) / df["chronic_daily"],
            np.nan,
        )
        df["b2b"] = (played & played.shift(1, fill_value=False)).values
        z = _game_minutes_z(day_minutes)
        df["min_z"] = z.values
        df["spike_z_7d"] = z.rolling(config.ACUTE_DAYS, min_periods=1).max().values
        frames.append(_flag(df))

    return pd.concat(frames, ignore_index=True)


def league_table(daily: pd.DataFrame, as_of: pd.Timestamp | str) -> pd.DataFrame:
    """One row per player as of a date. Trailing windows mean no future leaks in."""
    as_of = pd.Timestamp(as_of)
    return daily[daily["date"] == as_of].reset_index(drop=True)


def player_series(daily: pd.DataFrame, player_id) -> pd.DataFrame:
    """A single player's contiguous daily grid, for charting."""
    return (
        daily[daily["player_id"] == player_id]
        .sort_values("date")
        .reset_index(drop=True)
    )
