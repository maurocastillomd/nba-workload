"""Published thresholds for the workload flag system.

Every flag in the app traces back to a constant on this page.

There is deliberately NO acute:chronic workload ratio here. The ACWR was
dropped as a decision input after the methodological critiques (Impellizzeri
et al. 2020; Lolli et al. 2019 on mathematical coupling) and failed
replications. What replaced it: absolute week-over-week change, schedule
density, and spikes referenced to the player's own baseline.
"""

# --- rolling windows (calendar days) ---
ACUTE_DAYS = 7
CHRONIC_DAYS = 28  # exposure base window (descriptive; matches common practice)
CHRONIC_FLOOR_DAILY = 5.0  # min/day; below this a player has no meaningful base

# --- week-over-week ramp (Cross et al. 2016: large weekly changes carry risk) ---
# an NBA week naturally swings by one game (3 games -> 4 games = +33% at equal
# minutes), so the thresholds sit above calendar oscillation, and a jump must
# also clear an absolute floor of about 1.5 extra games' worth of minutes
RAMP_MIN_ACUTE = 90.0    # this week must be a real workload before a jump matters
RAMP_PRIOR_FLOOR = 30.0  # prior week below this -> percent change is meaningless
RAMP_MIN_DELTA = 45.0    # minutes; minimum absolute increase to count at all
RAMP_AMBER_PCT = 0.40    # +1 point
RAMP_RED_PCT = 0.75      # +2 points
# established player (chronic rated) coming off a near-zero week into a big
# one: "surge after a quiet week", +2 points

# --- low-chronic ramp-up (return from layoff straight into heavy minutes) ---
LOW_CHRONIC_ACUTE_MIN = 60.0  # acute-week minutes that make a low-chronic week a spike (+2)

# --- schedule density ---
GAMES_7D_HIGH = 4   # +1 point at 4+ games in 7 days
# back-to-back: +1 point

# --- individual minutes baseline (z-score vs the player's own prior 28 days) ---
MIN_Z_SPIKE = 1.5          # +1 point if a game in the last 7 days spiked above this
MIN_PRIOR_GAMES_FOR_Z = 3  # fewer prior games -> no baseline, no z
Z_STD_FLOOR = 4.0          # minutes; keeps tiny stds from exploding the z

# --- flag states ---
AMBER_POINTS = 2
RED_POINTS = 3
