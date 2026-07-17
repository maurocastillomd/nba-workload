"""Tests for the deterministic workload engine.

Every number in the app comes from this engine. These tests are the contract.
"""
import pandas as pd
import pytest

from nba_workload.engine import (
    compute_daily_metrics,
    league_table,
    player_series,
)
from nba_workload import config


def make_games(rows):
    """rows: list of (player_id, name, team, date_str, minutes)"""
    df = pd.DataFrame(
        rows, columns=["player_id", "player_name", "team", "game_date", "minutes"]
    )
    df["game_date"] = pd.to_datetime(df["game_date"])
    return df


def steady_player(player_id=1, name="Steady Vet", team="ORL",
                  start="2026-01-01", n_games=14, every_n_days=2, minutes=28):
    """A player on a clean every-other-day schedule at constant minutes."""
    dates = pd.date_range(start, periods=n_games, freq=f"{every_n_days}D")
    return make_games(
        [(player_id, name, team, d.strftime("%Y-%m-%d"), minutes) for d in dates]
    )


def get_day(daily, player_id, date):
    row = daily[(daily["player_id"] == player_id) & (daily["date"] == pd.Timestamp(date))]
    assert len(row) == 1, f"expected exactly one row for {player_id} on {date}"
    return row.iloc[0]


# ---------------------------------------------------------------- windows

def test_acute_7d_sums_minutes_in_trailing_window():
    games = make_games([
        (1, "A", "ORL", "2026-01-01", 30),
        (1, "A", "ORL", "2026-01-03", 30),
        (1, "A", "ORL", "2026-01-05", 30),
    ])
    daily = compute_daily_metrics(games)
    # window is as-of-day inclusive, 7 calendar days
    assert get_day(daily, 1, "2026-01-05")["acute_7d"] == 90
    # on Jan 9 the Jan 1 game (8 days back) has dropped out; Jan 3 and 5 remain
    assert get_day(daily, 1, "2026-01-09")["acute_7d"] == 60


def test_chronic_28d_is_daily_mean_of_minutes():
    # 10 games x 28 minutes spread inside a 28-day window ending Jan 28
    dates = [f"2026-01-{d:02d}" for d in range(1, 29, 3)][:10]
    games = make_games([(1, "A", "ORL", d, 28) for d in dates])
    daily = compute_daily_metrics(games)
    row = get_day(daily, 1, "2026-01-28")
    assert row["chronic_daily"] == pytest.approx(10 * 28 / 28)


def test_acwr_is_acute_daily_over_chronic_daily():
    games = steady_player()
    daily = compute_daily_metrics(games)
    last_date = games["game_date"].max()
    row = get_day(daily, 1, last_date)
    expected = (row["acute_7d"] / 7) / row["chronic_daily"]
    assert row["acwr"] == pytest.approx(expected)


def test_acwr_not_rated_below_chronic_floor():
    # a single early game: chronic is tiny, ACWR would be garbage
    games = make_games([(1, "A", "ORL", "2026-01-01", 6)])
    daily = compute_daily_metrics(games)
    assert pd.isna(get_day(daily, 1, "2026-01-01")["acwr"])


# ---------------------------------------------------------------- schedule density

def test_games_7d_counts_games_in_window():
    games = make_games([
        (1, "A", "ORL", "2026-01-01", 20),
        (1, "A", "ORL", "2026-01-02", 20),
        (1, "A", "ORL", "2026-01-04", 20),
        (1, "A", "ORL", "2026-01-06", 20),
    ])
    daily = compute_daily_metrics(games)
    assert get_day(daily, 1, "2026-01-06")["games_7d"] == 4
    assert get_day(daily, 1, "2026-01-09")["games_7d"] == 2


def test_b2b_true_only_when_played_today_and_yesterday():
    games = make_games([
        (1, "A", "ORL", "2026-01-03", 20),
        (1, "A", "ORL", "2026-01-04", 20),
        (1, "A", "ORL", "2026-01-06", 20),
    ])
    daily = compute_daily_metrics(games)
    assert bool(get_day(daily, 1, "2026-01-04")["b2b"]) is True
    assert bool(get_day(daily, 1, "2026-01-06")["b2b"]) is False
    assert bool(get_day(daily, 1, "2026-01-05")["b2b"]) is False


# ---------------------------------------------------------------- individual baseline z

def test_minutes_z_flags_spike_vs_own_baseline():
    # 8 games at ~20 minutes, then a 40-minute game
    rows = [(1, "A", "ORL", f"2026-01-{d:02d}", m)
            for d, m in zip(range(1, 17, 2), [20, 21, 19, 20, 21, 19, 20, 20])]
    rows.append((1, "A", "ORL", "2026-01-17", 40))
    games = make_games(rows)
    daily = compute_daily_metrics(games)
    row = get_day(daily, 1, "2026-01-17")
    assert row["min_z"] > config.MIN_Z_SPIKE


def test_minutes_z_requires_minimum_history():
    games = make_games([
        (1, "A", "ORL", "2026-01-01", 20),
        (1, "A", "ORL", "2026-01-03", 20),
        (1, "A", "ORL", "2026-01-05", 40),
    ])
    daily = compute_daily_metrics(games)
    # only 2 prior games -> no individual baseline yet
    assert pd.isna(get_day(daily, 1, "2026-01-05")["min_z"])


# ---------------------------------------------------------------- flags

def test_steady_schedule_is_green():
    games = steady_player()
    daily = compute_daily_metrics(games)
    row = get_day(daily, 1, games["game_date"].max())
    assert row["state"] == "GREEN"


def test_congestion_plus_spike_goes_red():
    # established ~24 min/game baseline, then a brutal week:
    # 4 games in 7 days incl. a back-to-back, with a big minutes spike
    rows = [(1, "A", "ORL", d.strftime("%Y-%m-%d"), 24)
            for d in pd.date_range("2026-01-01", periods=10, freq="3D")]
    rows += [
        (1, "A", "ORL", "2026-01-30", 38),
        (1, "A", "ORL", "2026-02-01", 40),
        (1, "A", "ORL", "2026-02-03", 40),
        (1, "A", "ORL", "2026-02-04", 42),
    ]
    games = make_games(rows)
    daily = compute_daily_metrics(games)
    row = get_day(daily, 1, "2026-02-04")
    assert row["state"] == "RED"
    assert row["risk_points"] >= config.RED_POINTS


def test_return_from_layoff_into_heavy_week_is_flagged():
    # 3 early games, a 5-week layoff, then two 35-minute games in 3 days.
    # chronic is near zero -> classic low-chronic ramp-up spike
    games = make_games([
        (1, "A", "ORL", "2026-01-01", 30),
        (1, "A", "ORL", "2026-01-03", 30),
        (1, "A", "ORL", "2026-01-05", 30),
        (1, "A", "ORL", "2026-02-12", 35),
        (1, "A", "ORL", "2026-02-14", 35),
    ])
    daily = compute_daily_metrics(games)
    row = get_day(daily, 1, "2026-02-14")
    assert row["state"] in ("AMBER", "RED")
    assert "low-chronic" in row["reasons"]


def test_reasons_name_the_contributing_rules():
    rows = [(1, "A", "ORL", d.strftime("%Y-%m-%d"), 24)
            for d in pd.date_range("2026-01-01", periods=10, freq="3D")]
    rows += [
        (1, "A", "ORL", "2026-01-30", 38),
        (1, "A", "ORL", "2026-02-01", 40),
        (1, "A", "ORL", "2026-02-03", 40),
        (1, "A", "ORL", "2026-02-04", 42),
    ]
    games = make_games(rows)
    daily = compute_daily_metrics(games)
    reasons = get_day(daily, 1, "2026-02-04")["reasons"]
    assert "back-to-back" in reasons
    assert "4 games in 7 days" in reasons


# ---------------------------------------------------------------- table + series

def test_league_table_one_row_per_player_as_of_date():
    games = pd.concat([
        steady_player(1, "One", "ORL"),
        steady_player(2, "Two", "MIA", minutes=32),
    ])
    daily = compute_daily_metrics(games)
    table = league_table(daily, as_of="2026-01-20")
    assert len(table) == 2
    assert set(table["player_id"]) == {1, 2}
    assert (table["date"] == pd.Timestamp("2026-01-20")).all()


def test_league_table_as_of_excludes_future_information():
    games = steady_player()
    daily = compute_daily_metrics(games)
    table = league_table(daily, as_of="2026-01-10")
    row = table[table["player_id"] == 1].iloc[0]
    # only games on Jan 1,3,5,7,9 exist by Jan 10 -> acute window (Jan 4-10) holds 3 games
    assert row["acute_7d"] == 3 * 28


def test_player_series_is_a_contiguous_daily_grid():
    games = steady_player(n_games=5)
    daily = compute_daily_metrics(games)
    series = player_series(daily, player_id=1)
    dates = series["date"]
    assert (dates.diff().dropna() == pd.Timedelta(days=1)).all()
    assert {"minutes", "acute_7d", "chronic_daily", "acwr", "state"} <= set(series.columns)
