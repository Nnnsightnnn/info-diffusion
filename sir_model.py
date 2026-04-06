"""
v0.1 — Core SIR Diffusion Model
================================
Deterministic SIR-style model for information spread through a population.

The question: if 10 people watch your video and start talking about it,
how long until the information diffuses through the broader zeitgeist?

States
------
  S (Susceptible)  : Haven't heard it yet
  I (Informed)     : Know it, actively spreading it in conversation
  R (Recovered)    : Know it, but no longer actively spreading

Discrete-time update equations
-------------------------------
  new_informed(t) = β · S(t) · I(t) / N
  new_silent(t)   = γ · I(t)

  S(t+1) = S(t) − new_informed(t)
  I(t+1) = I(t) + new_informed(t) − new_silent(t)
  R(t+1) = R(t) + new_silent(t)

  β = conversation_rate × spread_probability   (effective contact rate)
  γ = recovery_rate                             (rate of going silent)
  R₀ = β / γ                                   (viral coefficient)

  R₀ > 1  →  spreads virally
  R₀ = 1  →  marginal / endemic
  R₀ < 1  →  fizzles out
"""

from dataclasses import dataclass
from typing import List, Optional


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class DiffusionParams:
    seed_viewers: int = 10              # Initial informed population
    population_size: int = 1_000_000   # Total reachable population
    conversation_rate: float = 3.0     # Avg people told per day per informed person
    spread_probability: float = 0.15   # Prob a listener becomes an active spreader
    recovery_rate: float = 0.10        # Daily rate: informed → silent (γ)
    days_to_simulate: int = 90
    label: str = "default"

    @property
    def beta(self) -> float:
        """Effective contact rate β = conversation_rate × spread_probability."""
        return self.conversation_rate * self.spread_probability

    @property
    def R0(self) -> float:
        """Basic reproduction number R₀ = β / γ.
        Each active spreader spawns R₀ new spreaders before going silent."""
        return self.beta / self.recovery_rate


@dataclass
class DaySnapshot:
    day: int
    susceptible: int
    informed: int       # Actively spreading
    recovered: int      # Know it, no longer spreading
    pct_active: float   # % of population currently active spreaders
    pct_reached: float  # % who have ever heard it (informed + recovered)

    @property
    def total_reached(self) -> int:
        return self.informed + self.recovered


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

def run_sir(params: DiffusionParams) -> List[DaySnapshot]:
    """Run deterministic SIR simulation. Returns one snapshot per day (day 0 = initial state)."""
    N = params.population_size
    beta = params.beta
    gamma = params.recovery_rate

    S = float(N - params.seed_viewers)
    I = float(params.seed_viewers)
    R = 0.0

    snapshots: List[DaySnapshot] = []

    for day in range(params.days_to_simulate + 1):
        # Record state before updating
        snapshots.append(DaySnapshot(
            day=day,
            susceptible=round(S),
            informed=round(I),
            recovered=round(R),
            pct_active=round(100.0 * I / N, 4),
            pct_reached=round(100.0 * (I + R) / N, 4),
        ))

        # Euler step
        new_informed = beta * S * I / N
        new_silent = gamma * I

        S = max(0.0, S - new_informed)
        I = max(0.0, I + new_informed - new_silent)
        R = min(float(N), R + new_silent)

    return snapshots


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def summarize(snapshots: List[DaySnapshot], params: DiffusionParams) -> dict:
    """Compute key metrics from a completed simulation run."""
    N = params.population_size
    peak = max(snapshots, key=lambda s: s.informed)
    final = snapshots[-1]

    def day_crossing(threshold_pct: float) -> Optional[int]:
        for s in snapshots:
            if s.pct_reached >= threshold_pct:
                return s.day
        return None

    return {
        "label": params.label,
        "R0": round(params.R0, 2),
        "beta": round(params.beta, 4),
        "gamma": params.recovery_rate,
        "peak_informed": peak.informed,
        "peak_day": peak.day,
        "day_1pct": day_crossing(1.0),
        "day_10pct": day_crossing(10.0),
        "day_50pct": day_crossing(50.0),
        "final_reach_pct": final.pct_reached,
        "final_reached": final.total_reached,
    }


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def print_summary(s: dict) -> None:
    """Pretty-print simulation summary to stdout."""
    viral = "VIRAL" if s["R0"] > 1 else "FIZZLE"
    line = "─" * 46
    print(f"\n  ┌{line}┐")
    print(f"  │{'Info Diffusion Model — v0.1 Summary':^46}│")
    print(f"  ├{line}┤")
    print(f"  │  Scenario  : {s['label']:<33}│")
    print(f"  │  R₀ = β/γ  : {s['R0']:<7.2f}  ({viral}){'':<18}│")
    print(f"  │  β (eff.)  : {s['beta']:<7.4f}   γ : {s['gamma']:<20.4f}│")
    print(f"  ├{line}┤")
    print(f"  │  Peak active spreaders : {s['peak_informed']:>9,}  (day {s['peak_day']:>3})  │")

    for label, key in [("1%  reached", "day_1pct"), ("10% reached", "day_10pct"), ("50% reached", "day_50pct")]:
        val = s[key]
        val_str = f"day {val:>4}" if val is not None else "never    "
        print(f"  │  {label} : {val_str:>20}{'':<12}│")

    print(f"  │  Final reach : {s['final_reach_pct']:>6.2f}%  ({s['final_reached']:>12,} people)  │")
    print(f"  └{line}┘\n")


def print_timeline(snapshots: List[DaySnapshot], interval: int = 5) -> None:
    """ASCII timeline — one row every `interval` days."""
    bar_width = 40
    header = f"  {'Day':>4}  {'Active':>10}  {'Reached':>12}  {'%':>6}  Progress"
    print(header)
    print("  " + "─" * (len(header) - 2))
    for s in snapshots:
        if s.day % interval == 0 or s.day == snapshots[-1].day:
            filled = int(s.pct_reached / 100 * bar_width)
            bar = "█" * filled + "░" * (bar_width - filled)
            print(f"  {s.day:>4}  {s.informed:>10,}  {s.total_reached:>12,}  {s.pct_reached:>5.1f}%  {bar}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    params = DiffusionParams(
        seed_viewers=10,
        population_size=1_000_000,
        conversation_rate=3.0,
        spread_probability=0.15,
        recovery_rate=0.10,
        days_to_simulate=90,
        label="baseline — 10 viewers, pop 1M",
    )

    print(f"\n  Viral coefficient  R₀ = {params.beta:.3f} / {params.recovery_rate:.3f} = {params.R0:.2f}")
    print(f"  {'Information spreads!' if params.R0 > 1 else 'Information fizzles out.'}\n")

    snapshots = run_sir(params)
    stats = summarize(snapshots, params)
    print_summary(stats)
    print_timeline(snapshots, interval=5)
