"""
v0.4 — Interactive Scenario Explorer
======================================
A fun CLI tool to instantly explore "what if" questions about
information spread. Set parameters, pick a preset, see results.

Usage:
    python3 explore.py                    # interactive menu
    python3 explore.py --preset viral     # jump to a preset
    python3 explore.py --seeds 500 --conv 4.0 --spread 0.2
"""

import argparse
import sys
import time

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.prompt import Prompt, FloatPrompt, IntPrompt, Confirm
    from rich.columns import Columns
    from rich import box
    from rich.text import Text
    from rich.progress import track
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

from sir_model import DiffusionParams, run_sir, summarize, print_timeline
from monte_carlo import run_monte_carlo
from presets import PRESETS, PRESETS_BY_SLUG
import visualize

console = Console() if HAS_RICH else None


# ── Display helpers ───────────────────────────────────────────────────────────
def _r0_color(r0: float) -> str:
    if r0 < 1:   return "red"
    if r0 < 2:   return "yellow"
    if r0 < 4:   return "green"
    return "bright_green"

def _bar(pct: float, width: int = 35) -> str:
    filled = int(pct / 100 * width)
    return "█" * filled + "░" * (width - filled)

def show_results(params: DiffusionParams, run_mc: bool = True):
    """Run simulation and display rich results panel."""
    snapshots = run_sir(params)
    stats     = summarize(snapshots, params)
    N         = params.population_size

    if HAS_RICH:
        # ── Summary panel ──
        r0_col = _r0_color(params.R0)
        verdict = "VIRAL 🔥" if params.R0 > 1 else "FIZZLE 💨"

        lines = [
            f"[bold]Viral coefficient R₀:[/bold]  [{r0_col}]{params.R0:.2f}[/{r0_col}]  →  [{r0_col}]{verdict}[/{r0_col}]",
            f"[bold]Peak active spreaders:[/bold]  {stats['peak_informed']:,}  [dim](day {stats['peak_day']})[/dim]",
            f"[bold]Final reach:[/bold]            {stats['final_reach_pct']:.1f}%  [dim]({stats['final_reached']:,} / {N:,} people)[/dim]",
            "",
        ]
        for label, key in [("1%", "day_1pct"), ("10%", "day_10pct"), ("50%", "day_50pct")]:
            val = stats[key]
            val_str = f"day {val}" if val is not None else "[red]never[/red]"
            lines.append(f"  Reached {label} of population: {val_str}")

        console.print(Panel("\n".join(lines), title=f"[bold cyan]{params.label}[/bold cyan]",
                            border_style="cyan", padding=(1, 2)))

        # ── Timeline bar chart ──
        table = Table(box=box.SIMPLE, show_header=True, header_style="bold dim",
                      pad_edge=False)
        table.add_column("Day",      style="dim", width=5,  justify="right")
        table.add_column("Active",   width=12, justify="right")
        table.add_column("Reached",  width=14, justify="right")
        table.add_column("%",        width=6,  justify="right")
        table.add_column("Progress", width=38)

        for s in snapshots:
            if s.day % 5 == 0 or s.day == params.days_to_simulate:
                pct = s.pct_reached
                color = _r0_color(min(params.R0, 4))
                bar_str = f"[{color}]{_bar(pct)}[/{color}]"
                table.add_row(
                    str(s.day),
                    f"{s.informed:,}",
                    f"{s.total_reached:,}",
                    f"{pct:.1f}%",
                    bar_str,
                )
        console.print(table)

    else:
        # Plain fallback
        print_timeline(snapshots, interval=5)

    # ── Monte Carlo ──
    if run_mc:
        if HAS_RICH:
            console.print("\n[dim]Running 150 Monte Carlo trials for variance...[/dim]")
        mc      = run_monte_carlo(params, n_trials=150)
        final   = mc.final_reach() / N * 100
        d50     = mc.days_to_pct(50)
        valid50 = d50[~__import__("numpy").isnan(d50)]

        if HAS_RICH:
            mc_lines = [
                f"Final reach — mean: [cyan]{final.mean():.1f}%[/cyan]  "
                f"std: {final.std():.1f}%  "
                f"range: [{final.min():.1f}%, {final.max():.1f}%]",
            ]
            if len(valid50):
                mc_lines.append(
                    f"Days to 50%  — mean: [cyan]{valid50.mean():.1f}[/cyan]  "
                    f"std: {valid50.std():.1f}  "
                    f"range: [{valid50.min():.0f}, {valid50.max():.0f}]"
                )
            console.print(Panel("\n".join(mc_lines), title="[bold]Monte Carlo variance[/bold]",
                                border_style="dim", padding=(0, 2)))



# ── Interactive menu ──────────────────────────────────────────────────────────
def interactive_menu():
    if not HAS_RICH:
        print("Install 'rich' for the best experience: pip install rich")

    while True:
        if HAS_RICH:
            console.rule("[bold cyan]📡 Info Diffusion Explorer[/bold cyan]")
            console.print("\n[bold]Choose a scenario:[/bold]\n")
            for p in PRESETS:
                console.print(f"  [cyan]{p.slug:<12}[/cyan] {p.display}")
                console.print(f"  {'':12} [dim]{p.desc}[/dim]")
            console.print(f"\n  [cyan]{'custom':<12}[/cyan] Enter your own parameters")
            console.print(f"  [cyan]{'charts':<12}[/cyan] Regenerate all visualization charts")
            console.print(f"  [cyan]{'quit':<12}[/cyan] Exit\n")
            choice = Prompt.ask("[bold]→[/bold] Pick a scenario", default="small")
        else:
            print("\n--- Info Diffusion Explorer ---")
            for p in PRESETS:
                print(f"  {p.slug:12} {p.display}")
            print("  custom       Enter custom parameters")
            print("  charts       Regenerate charts")
            print("  quit         Exit")
            choice = input("\nPick a scenario: ").strip().lower()

        if choice == "quit":
            break

        elif choice == "charts":
            if HAS_RICH:
                console.print("\n[yellow]Generating all 3 charts...[/yellow]")
            visualize.plot_scurve(DiffusionParams())
            visualize.plot_seed_comparison()
            visualize.plot_sensitivity()
            if HAS_RICH:
                console.print("[green]✓ Charts saved to output/[/green]\n")

        elif choice == "custom":
            if HAS_RICH:
                console.print("\n[bold]Custom parameters[/bold] (press Enter to keep defaults)\n")
                seeds  = IntPrompt.ask("  Seed viewers",       default=10)
                pop    = IntPrompt.ask("  Population size",    default=1_000_000)
                conv   = FloatPrompt.ask("  Conversation rate", default=3.0)
                spread = FloatPrompt.ask("  Spread probability",default=0.15)
                recov  = FloatPrompt.ask("  Recovery rate",     default=0.10)
                days   = IntPrompt.ask("  Days to simulate",   default=90)
            else:
                seeds  = int(input("  Seed viewers [10]: ") or 10)
                pop    = int(input("  Population [1000000]: ") or 1_000_000)
                conv   = float(input("  Conversation rate [3.0]: ") or 3.0)
                spread = float(input("  Spread probability [0.15]: ") or 0.15)
                recov  = float(input("  Recovery rate [0.10]: ") or 0.10)
                days   = int(input("  Days to simulate [90]: ") or 90)

            params = DiffusionParams(
                seed_viewers=seeds, population_size=pop,
                conversation_rate=conv, spread_probability=spread,
                recovery_rate=recov, days_to_simulate=days,
                label=f"custom — {seeds:,} seeds / pop {pop:,}",
            )
            show_results(params)

        elif choice in PRESETS_BY_SLUG:
            preset = PRESETS_BY_SLUG[choice]
            params = DiffusionParams(**preset.params(), days_to_simulate=90, label=preset.display)
            show_results(params)

        else:
            if HAS_RICH:
                console.print(f"[red]Unknown choice: {choice!r}[/red]")
            else:
                print(f"Unknown: {choice}")

        if HAS_RICH:
            console.print()


# ── CLI entry point ───────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Info Diffusion Explorer — model how info spreads from a video")
    parser.add_argument("--preset",  choices=[p.slug for p in PRESETS],
                        help="Run a named preset directly")
    parser.add_argument("--seeds",   type=int,   default=None)
    parser.add_argument("--pop",     type=int,   default=1_000_000)
    parser.add_argument("--conv",    type=float, default=3.0,
                        help="Conversation rate (people told/day)")
    parser.add_argument("--spread",  type=float, default=0.15,
                        help="Spread probability")
    parser.add_argument("--recovery",type=float, default=0.10)
    parser.add_argument("--days",    type=int,   default=90)
    parser.add_argument("--no-mc",   action="store_true",
                        help="Skip Monte Carlo variance analysis")
    args = parser.parse_args()

    if args.preset:
        preset = PRESETS_BY_SLUG[args.preset]
        params = DiffusionParams(**preset.params(), days_to_simulate=90, label=preset.display)
        show_results(params, run_mc=not args.no_mc)
    elif args.seeds is not None:
        params = DiffusionParams(
            seed_viewers=args.seeds, population_size=args.pop,
            conversation_rate=args.conv, spread_probability=args.spread,
            recovery_rate=args.recovery, days_to_simulate=args.days,
            label=f"CLI — {args.seeds:,} seeds",
        )
        show_results(params, run_mc=not args.no_mc)
    else:
        interactive_menu()


if __name__ == "__main__":
    main()
