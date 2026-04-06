"""
v0.3 — Visualization Suite
============================
Three charts for exploring information diffusion dynamics:

1. S-curve  : Days vs % ever reached, with Monte Carlo confidence band
2. Seeds    : 10 vs 100 vs 1K vs 10K seed viewers comparison
3. Sensitivity: Viral coefficient vs days-to-50% and final reach
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from sir_model import DiffusionParams, run_sir
from monte_carlo import run_monte_carlo

os.makedirs("output", exist_ok=True)

# ── Shared dark style ────────────────────────────────────────────────────────
PALETTE = ["#4C9BE8", "#F28B30", "#2ECC71", "#E74C3C", "#9B59B6", "#1ABC9C"]
BG, PANEL, TEXT, GRID = "#0F1117", "#1A1D27", "#E8EAF0", "#2A2D3A"

def style(fig, axes):
    fig.patch.set_facecolor(BG)
    for ax in (axes if hasattr(axes, "__iter__") else [axes]):
        ax.set_facecolor(PANEL)
        ax.tick_params(colors=TEXT, labelsize=9)
        for lbl in [ax.xaxis.label, ax.yaxis.label, ax.title]:
            lbl.set_color(TEXT)
        for sp in ax.spines.values():
            sp.set_edgecolor(GRID)
        ax.grid(True, color=GRID, lw=0.5, ls="--", alpha=0.7)


# ── Chart 1: S-curve with MC confidence band ────────────────────────────────
def plot_scurve(params: DiffusionParams, n_trials=300,
                save="output/01_scurve.png"):
    print("  [1/3] S-curve + Monte Carlo band...")
    mc  = run_monte_carlo(params, n_trials=n_trials)
    det = run_sir(params)
    N   = params.population_size
    days = np.arange(params.days_to_simulate + 1)

    pct = mc.ever_reached_matrix / N * 100
    mean_, p5_, p95_ = pct.mean(0), np.percentile(pct, 5, 0), np.percentile(pct, 95, 0)
    det_pct = [s.pct_reached for s in det]

    fig, ax = plt.subplots(figsize=(10, 5.5))
    style(fig, ax)
    ax.fill_between(days, p5_, p95_, alpha=0.2, color=PALETTE[0], label="5–95th pct (MC)")
    ax.plot(days, mean_,   color=PALETTE[0], lw=2.5, label="MC mean")
    ax.plot(days, det_pct, color=PALETTE[1], lw=2, ls="--", label="Deterministic SIR")
    ax.axhline(50, color=GRID, lw=0.8, ls=":")
    ax.axhline(90, color=GRID, lw=0.8, ls=":")
    ax.text(params.days_to_simulate * 0.98, 51.5, "50%", color=TEXT,
            fontsize=8, ha="right")
    ax.text(params.days_to_simulate * 0.98, 91.5, "90%", color=TEXT,
            fontsize=8, ha="right")
    ax.set_xlabel("Days since first viewers", fontsize=11)
    ax.set_ylabel("% of population ever reached", fontsize=11)
    ax.set_title(
        f"Information S-Curve  ·  seed={params.seed_viewers:,}  "
        f"pop={N/1e6:.1f}M  R₀={params.R0:.1f}",
        fontsize=13, fontweight="bold", pad=12)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))
    ax.set_xlim(0, params.days_to_simulate)
    ax.set_ylim(-2, 103)
    ax.legend(facecolor=PANEL, edgecolor=GRID, labelcolor=TEXT, fontsize=9)
    plt.tight_layout()
    fig.savefig(save, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"     → {save}")


# ── Chart 2: Seed viewer comparison ─────────────────────────────────────────
def plot_seed_comparison(save="output/02_seed_comparison.png"):
    print("  [2/3] Seed comparison chart...")
    configs = [
        (10,     "Small creator (10 views)",    PALETTE[0]),
        (100,    "Growing channel (100 views)", PALETTE[1]),
        (1_000,  "Mid creator (1K views)",      PALETTE[2]),
        (10_000, "Big creator (10K views)",     PALETTE[3]),
    ]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5))
    style(fig, [ax1, ax2])

    for seeds, label, color in configs:
        p   = DiffusionParams(seed_viewers=seeds)
        det = run_sir(p)
        xs  = [s.day for s in det]
        ax1.plot(xs, [s.pct_active  for s in det], color=color, lw=2, label=label)
        ax2.plot(xs, [s.pct_reached for s in det], color=color, lw=2, label=label)

    for ax, title, ylab in [
        (ax1, "Active Buzz  (currently informed)", "% population actively spreading"),
        (ax2, "Total Reach  (ever heard about it)", "% population ever reached"),
    ]:
        ax.set_title(title, fontsize=12, fontweight="bold", pad=10)
        ax.set_xlabel("Days", fontsize=10)
        ax.set_ylabel(ylab, fontsize=10)
        ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))
        ax.set_xlim(0, 90)
        ax.legend(facecolor=PANEL, edgecolor=GRID, labelcolor=TEXT, fontsize=8.5)

    fig.suptitle("Seed Viewers Comparison — Same virality (R₀=4.5), different starting points",
                 fontsize=13, fontweight="bold", color=TEXT, y=1.01)
    plt.tight_layout()
    fig.savefig(save, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"     → {save}")


# ── Chart 3: Viral coefficient sensitivity ───────────────────────────────────
def plot_sensitivity(save="output/03_sensitivity.png"):
    print("  [3/3] Sensitivity / viral coefficient plot...")
    conv_rates   = np.linspace(0.5, 6.0, 45)
    spread_probs = [0.05, 0.10, 0.15, 0.20, 0.25]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5))
    style(fig, [ax1, ax2])

    for i, sp in enumerate(spread_probs):
        d50s, reaches, r0s = [], [], []
        for cr in conv_rates:
            p   = DiffusionParams(conversation_rate=cr, spread_probability=sp,
                                  days_to_simulate=120)
            det = run_sir(p)
            r0s.append(p.R0)
            crossed = [s.day for s in det if s.pct_reached >= 50]
            d50s.append(crossed[0] if crossed else 120)
            reaches.append(det[-1].pct_reached)

        c   = PALETTE[i % len(PALETTE)]
        lbl = f"spread_prob={sp:.2f}"
        ax1.plot(r0s, d50s,   color=c, lw=2, label=lbl)
        ax2.plot(r0s, reaches, color=c, lw=2, label=lbl)

    for ax in [ax1, ax2]:
        ax.axvline(1, color="#E74C3C", lw=1.2, ls="--", alpha=0.8,
                   label="R₀=1 tipping point")

    ax1.set_title("Speed: Days to reach 50% of population",
                  fontsize=12, fontweight="bold")
    ax1.set_xlabel("Viral coefficient R₀  (conv_rate × spread_prob / γ)", fontsize=9)
    ax1.set_ylabel("Days to 50% reach", fontsize=10)
    ax1.set_ylim(0, 125)
    ax1.legend(facecolor=PANEL, edgecolor=GRID, labelcolor=TEXT, fontsize=8)

    ax2.set_title("Ceiling: Final % population ever reached",
                  fontsize=12, fontweight="bold")
    ax2.set_xlabel("Viral coefficient R₀", fontsize=9)
    ax2.set_ylabel("% ever reached (day 120)", fontsize=10)
    ax2.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))
    ax2.legend(facecolor=PANEL, edgecolor=GRID, labelcolor=TEXT, fontsize=8)

    fig.suptitle("Sensitivity to Viral Coefficient R₀  ·  How virality changes speed & ceiling",
                 fontsize=12, fontweight="bold", color=TEXT, y=1.01)
    plt.tight_layout()
    fig.savefig(save, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"     → {save}")


# ── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n📊 Generating visualization suite (v0.3)...")
    params = DiffusionParams()
    plot_scurve(params)
    plot_seed_comparison()
    plot_sensitivity()
    print("\n✅ All 3 charts saved to output/\n")
