"""NBA Schedule Congestion & Workload Monitor.

Real public box-score minutes -> deterministic trailing-window engine -> flags.
Every number on this page comes from nba_workload/engine.py; the app only
displays. Built by Mauro Castillo, MD, MS, CSCS.
"""
import altair as alt
import pandas as pd
import streamlit as st

from nba_workload import config
from nba_workload.engine import compute_daily_metrics, league_table, player_series
from nba_workload.fetch import load_snapshot

# palette (validated: see README methods section)
BLUE = "#2563EB"     # 7-day rolling line
AMBER_LINE = "#B45309"  # 28-day rolling line
NEUTRAL_BAR = "#64748B"
STATE_COLORS = {"GREEN": "#15803D", "AMBER": "#F59E0B", "RED": "#991B1B"}
STATE_TEXT = {"GREEN": "#FFFFFF", "AMBER": "#1C1917", "RED": "#FFFFFF"}
INK = "#1C1917"

st.set_page_config(
    page_title="NBA Workload Monitor",
    page_icon=":material/monitor_heart:",
    layout="wide",
)


@st.cache_data(show_spinner="Computing league-wide workload metrics...")
def load_daily():
    games = load_snapshot()
    season = games["season"].iloc[0] if "season" in games.columns else "2025-26"
    daily = compute_daily_metrics(games, season_end=games["game_date"].max())
    return games, daily, season


games, daily, season = load_daily()
first_date = games["game_date"].min().date()
last_date = games["game_date"].max().date()

st.title("NBA Schedule Congestion & Workload Monitor")
st.caption(
    f"{season} regular season · real minutes from stats.nba.com · "
    f"data through {last_date:%b %d, %Y} · every flag is deterministic arithmetic, "
    "not a model's opinion"
)

# ---------------------------------------------------------------- controls
with st.sidebar:
    st.header("View")
    as_of = st.slider(
        "As of date",
        min_value=first_date,
        max_value=last_date,
        value=last_date,
        format="MMM D, YYYY",
        help="The table answers: who was in a risky workload window on this day? "
        "Trailing windows only — nothing after this date is used.",
    )
    teams = st.multiselect("Teams", sorted(daily["team"].unique()), default=[])
    hide_fringe = st.toggle(
        "Hide low-volume players",
        value=True,
        help=f"Hides players averaging under {config.CHRONIC_FLOOR_DAILY:.0f} min/day "
        "over the trailing 28 days, unless they are flagged.",
    )
    search = st.text_input("Find a player", placeholder="e.g. Bam Adebayo")

table = league_table(daily, pd.Timestamp(as_of))
if teams:
    table = table[table["team"].isin(teams)]
if hide_fringe:
    table = table[
        (table["chronic_daily"] >= config.CHRONIC_FLOOR_DAILY) | (table["state"] != "GREEN")
    ]
if search.strip():
    table = table[table["player_name"].str.contains(search.strip(), case=False)]
table = table.sort_values(["risk_points", "acute_7d"], ascending=False)

# ---------------------------------------------------------------- headline
c1, c2, c3, c4 = st.columns(4)
c1.metric("Red flags", int((table["state"] == "RED").sum()))
c2.metric("Amber flags", int((table["state"] == "AMBER").sum()))
c3.metric("Green", int((table["state"] == "GREEN").sum()))
c4.metric("Players in view", len(table))

# ---------------------------------------------------------------- league table
display = table[[
    "player_name", "team", "state", "risk_points", "reasons",
    "acute_7d", "games_7d", "chronic_daily", "acwr", "b2b",
]].rename(columns={
    "player_name": "Player", "team": "Team", "state": "State",
    "risk_points": "Pts", "reasons": "Why",
    "acute_7d": "Min, last 7d", "games_7d": "Games, 7d",
    "chronic_daily": "28d min/day", "acwr": "ACWR", "b2b": "B2B",
})


def paint_state(value):
    color = STATE_COLORS.get(value, "#FFFFFF")
    text = STATE_TEXT.get(value, INK)
    return f"background-color: {color}; color: {text}; font-weight: 600;"


st.dataframe(
    display.style.map(paint_state, subset=["State"]).format({
        "Min, last 7d": "{:.0f}", "Games, 7d": "{:.0f}",
        "28d min/day": "{:.1f}", "ACWR": "{:.2f}",
    }, na_rep="—"),
    width="stretch",
    height=430,
    hide_index=True,
    column_config={
        "Why": st.column_config.TextColumn(width="large"),
        "B2B": st.column_config.CheckboxColumn(help="Played yesterday and today"),
        "ACWR": st.column_config.NumberColumn(
            help="Acute:chronic workload ratio (7d avg / 28d avg). Context, not a verdict."
        ),
    },
)

# ---------------------------------------------------------------- player detail
st.divider()
st.subheader("Player detail")

options = table["player_name"].tolist() or sorted(daily["player_name"].unique())
picked = st.selectbox("Player", options, index=0)
picked_id = daily.loc[daily["player_name"] == picked, "player_id"].iloc[0]

series = player_series(daily, picked_id)
series = series[series["date"] <= pd.Timestamp(as_of)].copy()
series["acute_daily"] = series["acute_7d"] / config.ACUTE_DAYS

today = series.iloc[-1]
left, right = st.columns([3, 1])
with right:
    chip_bg = STATE_COLORS[today["state"]]
    chip_ink = STATE_TEXT[today["state"]]
    st.markdown(
        f'<span style="background:{chip_bg};color:{chip_ink};padding:4px 14px;'
        f'border-radius:6px;font-weight:700;">{today["state"]}</span>',
        unsafe_allow_html=True,
    )
    st.metric("Risk points", int(today["risk_points"]))
    st.metric("Minutes, last 7 days", f"{today['acute_7d']:.0f}")
    st.metric("28-day avg (min/day)", f"{today['chronic_daily']:.1f}")
    st.metric("ACWR", "not rated" if pd.isna(today["acwr"]) else f"{today['acwr']:.2f}")
    if today["reasons"]:
        st.markdown("**Why this flag**")
        for reason in today["reasons"].split("; "):
            st.markdown(f"- {reason}")
    else:
        st.markdown("**No risk rules firing** on this date.")

with left:
    lines = series.melt(
        id_vars=["date"],
        value_vars=["acute_daily", "chronic_daily"],
        var_name="window", value_name="value",
    )
    lines["window"] = lines["window"].map({
        "acute_daily": "7-day avg", "chronic_daily": "28-day avg",
    })

    hover = alt.selection_point(
        fields=["date"], nearest=True, on="pointermove", empty=False
    )

    bars = (
        alt.Chart(series[series["played"]])
        .mark_bar(color=NEUTRAL_BAR, opacity=0.45, width=3)
        .encode(
            x=alt.X("date:T", title=None, axis=alt.Axis(format="%b %e")),
            y=alt.Y("minutes:Q", title="Minutes per day"),
            tooltip=[
                alt.Tooltip("date:T", title="Game"),
                alt.Tooltip("minutes:Q", title="Minutes", format=".0f"),
                alt.Tooltip("min_z:Q", title="z vs own baseline", format=".2f"),
            ],
        )
    )
    line_layer = (
        alt.Chart(lines)
        .mark_line(strokeWidth=2)
        .encode(
            x="date:T",
            y=alt.Y("value:Q", title="Minutes per day"),
            color=alt.Color(
                "window:N",
                scale=alt.Scale(domain=["7-day avg", "28-day avg"],
                                range=[BLUE, AMBER_LINE]),
                legend=alt.Legend(title=None, orient="top"),
            ),
            strokeDash=alt.StrokeDash(
                "window:N",
                scale=alt.Scale(domain=["7-day avg", "28-day avg"],
                                range=[[1, 0], [6, 4]]),
                legend=None,
            ),
        )
    )
    points = line_layer.mark_point(size=70, filled=True).encode(
        opacity=alt.condition(hover, alt.value(1), alt.value(0)),
        tooltip=[
            alt.Tooltip("date:T"),
            alt.Tooltip("window:N", title="Window"),
            alt.Tooltip("value:Q", title="Min/day", format=".1f"),
        ],
    ).add_params(hover)
    rule = (
        alt.Chart(series)
        .mark_rule(color=INK, opacity=0.25)
        .encode(x="date:T")
        .transform_filter(hover)
    )
    load_chart = (bars + line_layer + points + rule).properties(
        height=300, width="container"
    )

    strip_data = series.copy()
    strip_data["date_end"] = strip_data["date"] + pd.Timedelta(days=1)
    strip = (
        alt.Chart(strip_data)
        .mark_rect(clip=True)
        .encode(
            x=alt.X("date:T", title=None, axis=None),
            x2="date_end:T",
            color=alt.Color(
                "state:N",
                scale=alt.Scale(domain=list(STATE_COLORS), range=list(STATE_COLORS.values())),
                legend=alt.Legend(title="Daily flag", orient="bottom"),
            ),
            tooltip=[
                alt.Tooltip("date:T"),
                alt.Tooltip("state:N", title="Flag"),
                alt.Tooltip("risk_points:Q", title="Points"),
                alt.Tooltip("reasons:N", title="Why"),
            ],
        )
        .properties(height=32, width="container")
    )

    st.altair_chart(
        alt.vconcat(load_chart, strip, spacing=6)
        .resolve_scale(x="shared", color="independent")
        .resolve_legend(color="independent"),
        use_container_width=True,
    )

# ---------------------------------------------------------------- methods
st.divider()
with st.expander("Methods, thresholds, and honest limitations"):
    st.markdown(f"""
**Data.** Official NBA box-score minutes for the {season} regular season via the
`nba_api` package (stats.nba.com). One row per player per game. The app never
estimates a number; if a value is missing, it says "not rated."

**Windows.** Acute load = trailing **{config.ACUTE_DAYS}-day** minutes.
Chronic load = trailing **{config.CHRONIC_DAYS}-day** minutes averaged per day
(fixed {config.CHRONIC_DAYS}-day denominator, off days count as zero).
ACWR = (acute/{config.ACUTE_DAYS}) / chronic. When the chronic base is under
**{config.CHRONIC_FLOOR_DAILY:.0f} min/day** the ratio is unstable and is not rated.

**Flag rules (points).**
- ACWR ≥ {config.ACWR_RED}: **+2** · ACWR ≥ {config.ACWR_AMBER}: **+1**
- Low-chronic ramp-up (≥ {config.LOW_CHRONIC_ACUTE_MIN:.0f} min in 7 days on an
  unrated chronic base, e.g. returning from a layoff): **+2**
- {config.GAMES_7D_HIGH}+ games in 7 days: **+1** · Back-to-back: **+1**
- A game in the last 7 days spiking above the player's own prior
  {config.CHRONIC_DAYS}-day baseline (z ≥ {config.MIN_Z_SPIKE}, minimum
  {config.MIN_PRIOR_GAMES_FOR_Z} prior games): **+1**

**RED ≥ {config.RED_POINTS} points · AMBER = {config.AMBER_POINTS} · GREEN otherwise.**

**Limitations, stated plainly.** Public minutes are a proxy, not a load
measurement: no practice load, no travel, no positional demands, no
force-plate or GPS data. ACWR itself is debated in the literature; here it is
one input among several, never a verdict. This is a monitoring lens for
conversation-starting, not medical advice and not an injury prediction model.
""")

st.caption(
    "Built by Mauro Castillo, MD, MS, CSCS · [maurocastillomd.com](https://maurocastillomd.com) · "
    "engine and thresholds are open source; every number is covered by automated tests."
)
