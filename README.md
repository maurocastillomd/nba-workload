# NBA Schedule Congestion & Workload Monitor

**Live app: https://nba-workload.streamlit.app**

A live answer to one question every basketball performance staff asks weekly:
**which players are entering a high-risk workload window right now?**

Real NBA box-score minutes go through a deterministic trailing-window engine.
The engine flags schedule congestion, minute spikes against each player's own
baseline, and return-from-layoff ramp-ups. Every number is arithmetic on public
data, covered by automated tests. No model writes a number.

![League table](docs/screenshot-table.png)

![Player detail](docs/screenshot-player.png)

## What it computes

For every player, every day of the season:

| Metric | Definition |
|---|---|
| Acute load | trailing 7-day minutes |
| Week-over-week ramp | change in 7-day minutes vs the 7 days before |
| Exposure base | trailing 28-day minutes, averaged per day (fixed denominator, off days count as zero) |
| Schedule density | games in the last 7 days; back-to-back detection |
| Minutes spike | z-score of each game vs the player's own prior 28 days of games (minimum 3 prior games) |

Flags are a transparent point system (thresholds in
[`nba_workload/config.py`](nba_workload/config.py)):

- Week up ≥ 75% **+2** · up ≥ 40% **+1** — only when this week is a real
  workload (90+ min) and the jump clears 45 absolute minutes, because an NBA
  calendar naturally swings by one game a week
- Surge after a quiet week (established player, near-zero week → 90+ min) **+2**
- Low-chronic ramp-up (60+ min in a week on no meaningful 28-day base, e.g. returning from a layoff) **+2**
- 4+ games in 7 days **+1** · back-to-back **+1** · minutes spike z ≥ 1.5 in the last 7 days **+1**

**RED ≥ 3 · AMBER = 2 · GREEN otherwise.** The "as of" slider replays any date
of the season using only information available on that date (trailing windows,
no leakage).

## Why there is no ACWR in this tool

The acute:chronic workload ratio was the industry default for a decade. It
did not survive scrutiny: the founding studies had methodological problems
(Impellizzeri et al. 2020), the coupled ratio correlates with itself by
construction (Lolli et al. 2019), and replications kept failing. A ratio also
hides the information a coach actually needs — an ACWR of 1.4 can mean 40
extra minutes or 8. This engine keeps the inputs the ratio was built from and
drops the ratio: absolute week-over-week change (Cross et al. 2016 on weekly
load changes), basketball-specific schedule density (Teramoto 2017, Lewis
2018 on NBA congestion), and spikes referenced to each player's own baseline
instead of a population constant.

## Run it

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest            # 20 tests on the engine
.venv/bin/streamlit run app.py
```

The repo ships with a data snapshot (`data/player_game_logs.parquet`, 2025-26
regular season, 26,568 player-game rows). To refresh from the NBA stats API:

```bash
.venv/bin/python scripts/refresh_data.py 2025-26
```

Run the refresh from a residential connection — stats.nba.com blocks most
cloud IPs, which is exactly why the app reads a committed snapshot instead of
calling the API at runtime.

## Architecture

```
stats.nba.com ──(nba_api, one call per season)──> data/*.parquet   [refresh script, local]
data/*.parquet ──> nba_workload/engine.py ──> daily player grid    [pure pandas, tested]
daily grid ──> app.py (Streamlit + Altair)                         [display only]
```

- `nba_workload/engine.py` — the entire model. Pure functions, no I/O.
- `nba_workload/config.py` — every threshold, one page.
- `tests/` — the contract: windows, ACWR, z-scores, flag rules, leak-free as-of slicing.
- `app.py` — league table, player detail chart, daily flag strip, methods page.

## Honest limitations

Public minutes are a proxy, not a load measurement: no practice load, no
travel, no positional demands, no force-plate or GPS data. The first two
weeks of a season read hot while baselines build. This is a monitoring lens
that starts conversations. It is not medical advice and not an injury
prediction model.

## Roadmap (deliberately not built yet)

- G League data (same engine, different league ID)
- Playoff games in the chronic window
- Travel distance and time-zone crossings
- Nightly in-season refresh via a scheduled local job

---

Built end-to-end by **Mauro Castillo, MD, MS, CSCS** —
[maurocastillomd.com](https://maurocastillomd.com)
