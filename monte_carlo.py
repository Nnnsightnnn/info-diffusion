"""
v0.2 — Stochastic Monte Carlo Simulation
==========================================
Adds randomness on top of the deterministic SIR model.

At each time step, instead of computing exact fractional flows,
we sample from binomial distributions:
  - new_informed ~ Binomial(S, beta * I/N)
  - new_silent   ~ Binomial(I, gamma)

Running N trials reveals the *variance* in outcomes — sometimes
a viral video takes off, sometimes the same content fizzles.
"""

import numpy as np
from dataclasses import dataclass, field
from sir_model import DiffusionParams, run_sir


@dataclass
class MonteCarloResults:
    trials: int
    days: int
    # Shape: (trials, days+1)
    informed_matrix: np.ndarray
    ever_reached_matrix: np.ndarray
    params: DiffusionParams

    def peak_reach(self) -> np.ndarray:
        """Max informed count per trial."""
        return self.informed_matrix.max(axis=1)

    def final_reach(self) -> np.ndarray:
        """% ever reached by end of sim, per trial."""
        return self.ever_reached_matrix[:, -1]

    def days_to_pct(self, pct: float) -> np.ndarray:
        """Days to reach pct% ever-reached, per trial. NaN if never reached."""
        threshold = pct / 100.0 * self.params.population_size
        results = np.full(self.trials, np.nan)
        for t in range(self.trials):
            crossed = np.where(self.ever_reached_matrix[t] >= threshold)[0]
            if len(crossed):
                results[t] = crossed[0]
        return results



def run_monte_carlo(params: DiffusionParams, n_trials: int = 200,
                    seed: int = 42) -> MonteCarloResults:
    """Run n_trials stochastic SIR simulations."""
    rng = np.random.default_rng(seed)
    N = params.population_size
    beta = params.conversation_rate * params.spread_probability
    gamma = params.recovery_rate
    days = params.days_to_simulate

    informed_matrix     = np.zeros((n_trials, days + 1), dtype=np.float64)
    ever_reached_matrix = np.zeros((n_trials, days + 1), dtype=np.float64)

    for t in range(n_trials):
        S = N - params.seed_viewers
        I = params.seed_viewers
        R = 0

        for day in range(days + 1):
            informed_matrix[t, day]     = I
            ever_reached_matrix[t, day] = I + R

            # Stochastic transitions — clamp to valid integer ranges
            p_infect = min(1.0, beta * I / N)
            new_informed = int(rng.binomial(int(S), p_infect))
            new_silent   = int(rng.binomial(int(I), gamma))

            S = max(0, S - new_informed)
            I = max(0, I + new_informed - new_silent)
            R = min(N, R + new_silent)

    return MonteCarloResults(
        trials=n_trials,
        days=days,
        informed_matrix=informed_matrix,
        ever_reached_matrix=ever_reached_matrix,
        params=params,
    )


def print_mc_summary(mc: MonteCarloResults):
    """Print variance analysis across Monte Carlo trials."""
    N = mc.params.population_size
    peak   = mc.peak_reach()
    final  = mc.final_reach() / N * 100
    d50    = mc.days_to_pct(50)

    # Get deterministic baseline
    det = run_sir(mc.params)
    det_peak  = max(r["informed"] for r in det)
    det_final = det[-1]["pct_ever_reached"]

    print("\n" + "="*65)
    print("  INFO DIFFUSION — MONTE CARLO ANALYSIS (v0.2)")
    print(f"  {mc.trials} trials  |  pop {N:,}  |  "
          f"seed {mc.params.seed_viewers:,} viewers")
    print("="*65)

    print(f"\n  {'Metric':<30} {'Mean':>10} {'Std':>10} {'Min':>10} {'Max':>10}")
    print("  " + "-"*62)
    print(f"  {'Peak informed':<30} {peak.mean():>10,.0f} {peak.std():>10,.0f} "
          f"{peak.min():>10,.0f} {peak.max():>10,.0f}")
    print(f"  {'% ever reached':<30} {final.mean():>9.1f}% {final.std():>9.1f}% "
          f"{final.min():>9.1f}% {final.max():>9.1f}%")
    valid_d50 = d50[~np.isnan(d50)]
    if len(valid_d50):
        print(f"  {'Days to 50% reached':<30} {valid_d50.mean():>10.1f} "
              f"{valid_d50.std():>10.1f} {valid_d50.min():>10.0f} "
              f"{valid_d50.max():>10.0f}")
    else:
        print(f"  {'Days to 50% reached':<30} {'never':>10}")

    print(f"\n  Deterministic baseline — peak: {det_peak:,}  |  "
          f"ever reached: {det_final:.1f}%")

    # Percentile breakdown
    print(f"\n  Percentile distribution of % ever reached:")
    for p in [5, 25, 50, 75, 95]:
        bar_len = int(np.percentile(final, p) / 2)
        bar = "█" * bar_len
        print(f"    p{p:2d}: {np.percentile(final, p):5.1f}%  {bar}")
    print()


if __name__ == "__main__":
    params = DiffusionParams()
    print("Running 200 Monte Carlo trials...")
    mc = run_monte_carlo(params, n_trials=200)
    print_mc_summary(mc)
