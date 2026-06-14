import os
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich import box
from src.comparison import AbilityDelta

console = Console()


def print_dungeon_table(
    deltas: list[AbilityDelta],
    dungeon_name: str,
    bracket: int,
    your_dps: float,
    top_n_dps: float,
    top_n: int,
) -> None:
    dps_gap = ((your_dps - top_n_dps) / top_n_dps * 100) if top_n_dps else 0.0
    gap_color = "green" if dps_gap >= 0 else "red"
    console.print(f"\n[bold]Dungeon Breakdown — {dungeon_name} +{bracket}[/bold]")
    console.print(
        f"Your DPS: [cyan]{your_dps:,.0f}[/cyan]  "
        f"Top {top_n} avg: [orange1]{top_n_dps:,.0f}[/orange1]  "
        f"Gap: [{gap_color}]{dps_gap:+.1f}%[/{gap_color}]\n"
    )
    header = (
        f"{'Ability':<24} {'Your Casts':>10} {'Top N Avg':>10} "
        f"{'Cast Δ':>8} {'Your GCD%':>10} {'Top N GCD%':>10} {'GCD Δ':>8}"
    )
    console.print(f"[dim]{header}[/dim]")
    for d in deltas:
        color = "green" if d.gcd_delta > 0 else ("red" if d.gcd_delta < 0 else "dim")
        row = (
            f"{d.ability_name:<24} {d.your_casts:>10} {d.top_n_avg:>10.1f} "
            f"{d.cast_delta:>+8.1f} {d.your_gcd_pct:>9.1f}% {d.top_n_gcd_pct:>9.1f}%"
        )
        console.print(f"{row} [{color}]{d.gcd_delta:>+8.1f}%[/{color}]")


def print_overview_results(results: list[dict]) -> None:
    console.print("\n[bold]Season Overview[/bold]\n")
    for r in results:
        console.print(
            f"[bold]{r['dungeon']} +{r['bracket']}[/bold]  "
            f"Clear time: {r['fight_duration_s']}s  "
            f"Top {r['top_n']} avg DPS: [orange1]{r['top_n_dps']:,.0f}[/orange1]"
        )
    console.print()


def print_compare_table(
    your_casts: dict[int, int],
    their_casts: dict[int, int],
    ability_names: dict[int, str],
    your_name: str,
    their_name: str,
) -> None:
    all_ids = sorted(
        set(your_casts) | set(their_casts),
        key=lambda i: your_casts.get(i, 0) + their_casts.get(i, 0),
        reverse=True,
    )
    console.print(f"\n[bold]1v1 — {your_name} vs {their_name}[/bold]\n")
    header = f"{'Ability':<24} {your_name[:16]:>16} {their_name[:16]:>16} {'Δ':>6}"
    console.print(f"[dim]{header}[/dim]")
    for aid in all_ids:
        yours = your_casts.get(aid, 0)
        theirs = their_casts.get(aid, 0)
        diff = yours - theirs
        color = "green" if diff > 0 else ("red" if diff < 0 else "dim")
        name = ability_names.get(aid, str(aid))
        row = f"{name:<24} {yours:>16} {theirs:>16}"
        console.print(f"{row} [{color}]{diff:>+6d}[/{color}]")
