"""Published thresholds for the workload flag system.

Every flag in the app traces back to a constant on this page.
ACWR is context, not a verdict: it contributes points, it never decides alone.
"""

# --- rolling windows (calendar days) ---
ACUTE_DAYS = 7
CHRONIC_DAYS = 28  # same chronic window as standard workload-management practice

# --- ACWR (acute:chronic workload ratio, coupled rolling averages) ---
ACWR_AMBER = 1.30   # +1 point
ACWR_RED = 1.50     # +2 points
CHRONIC_FLOOR_DAILY = 5.0  # min/day; below this the ratio is not rated (unstable denominator)

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
