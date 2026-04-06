"""
v0.1 — Core SIR Diffusion Model
================================
Deterministic SIR-style model for information spread.

S (Susceptible) → I (Informed) → R (Recovered/Silent)

The rate of new infections:
  dS/dt = -β * S * I / N
  dI/dt =  β * S * I / N - γ * I
  dR/dt =  γ * I

where β = conversation_rate * spread_probability
      γ = recovery_rate
"""

import csv
import os
from dataclasses import dataclass


@dataclass
class DiffusionParams:
    seed_viewers: int = 10
    population_size: int = 1_000_000
    conversation_rate: float = 3.0      # people told per day per informed person
    spread_probability: float = 0.15    # chance the listener cares / shares
    recovery_rate: float = 0.10         # rate informed -> silent per day
    days_to_simulate: int = 60


def run_sir(params: DiffusionParams) -> list:
    """Run deterministic SIR model; returns list of day-snapshot dicts."""
    N = params.population_size
    beta = params.conversation_rate * params.spread_probability
    gamma = params.recovery_rate

    S = float(N - params.seed_viewers)
    I = float(params.seed_viewers)
    R = 0.0

    results = []
    for day in range(params.days_to_simulate + 1):
        new_informed = beta * S * I / N
        new_silent   = gamma * I

        results.append({
            "day": day,
            "susceptible": round(S),
            "informed":    round(I),
            "recovered":   round(R),
            "pct_informed": round(100 * I / N, 4),
            "pct_ever_reached": round(100 * (I + R) / N, 4),
        })

        S = max(0, S - new_informed)
        I = max(0, I + new_informed - new_silent)
        R = min(N, R + new_silent)

    return results


def save_csv(results: list, path: str = "output/sir_results.csv") -> str:
    """Write results to CSV; returns file path."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    return path


def print_summary(results: list, params: DiffusionParams):
    """Print a clean summary table to stdout."""
    beta = params.conversation_rate * params.spread_probability
    k = beta / params.recovery_rate  # basic reproduction number R0
    peak = max(results, key=lambda r: r["informed"])
    final = results[-1]

    print("\n" + "="*60)
    print("  INFO DIFFUSION — SIR MODEL (v0.1)")
    print("="*60)
    print(f"  Population:       {params.population_size:>12,}")
    print(f"  Seed viewers:     {params.seed_viewers:>12,}")
    print(f"  Conversation rate:{params.conversation_rate:>12.1f} /day")
    print(f"  Spread prob:      {params.spread_probability:>12.2f}")
    print(f"  Recovery rate:    {params.recovery_rate:>12.2f} /day")
    print(f"  Viral coeff R0:   {k:>12.2f}  ({'VIRAL' if k>1 else 'FIZZLE'})")
    print("-"*60)
    print(f"  Peak informed:    {peak['informed']:>12,}  (day {peak['day']})")
    print(f"  Peak % pop:       {peak['pct_informed']:>11.2f}%")
    print(f"  Ever reached:     {final['pct_ever_reached']:>11.2f}%  "
          f"({round(final['informed']+final['recovered']):,} people)")
    print("="*60)

    # Print day-by-day table (every 5 days)
    print(f"\n  {'Day':>4}  {'Informed':>12}  {'% Informed':>10}  {'% Ever Reached':>15}")
    print("  " + "-"*46)
    for r in results:
        if r["day"] % 5 == 0 or r["day"] == params.days_to_simulate:
            print(f"  {r['day']:>4}  {r['informed']:>12,}  "
                  f"{r['pct_informed']:>9.3f}%  {r['pct_ever_reached']:>14.3f}%")
    print()


if __name__ == "__main__":
    params = DiffusionParams()
    results = run_sir(params)
    csv_path = save_csv(results)
    print_summary(results, params)
    print(f"  CSV saved to: {csv_path}\n")
