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


_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #0d0d0f; color: #ccc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 13px; padding: 24px 28px; }
h1 { color: #fff; font-size: 18px; margin-bottom: 4px; }
h2 { color: #fff; font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em; margin: 20px 0 10px; }
.meta { color: #666; font-size: 12px; margin-bottom: 20px; }
.cards { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 20px; }
.card { background: #141418; border: 1px solid #222; border-radius: 6px; padding: 12px 16px; min-width: 160px; }
.card .label { font-size: 10px; color: #555; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 4px; }
.card .value { font-size: 18px; font-weight: 700; }
table { width: 100%; border-collapse: collapse; margin-bottom: 24px; }
th { text-align: left; color: #555; font-size: 10px; text-transform: uppercase; letter-spacing: 0.06em; padding: 6px 10px; border-bottom: 1px solid #1e1e1e; }
td { padding: 7px 10px; border-bottom: 1px solid #181818; }
.pos { color: #2ecc71; font-weight: 600; }
.neg { color: #e74c3c; font-weight: 600; }
.neu { color: #555; }
.split { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.player-col { background: #141418; border: 1px solid #222; border-radius: 6px; padding: 14px; }
.player-col h3 { color: #fff; margin-bottom: 10px; font-size: 13px; }
"""

_HTML_FRAME = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>wow-wl-analyzer</title>
<style>{css}</style>
</head>
<body>{body}</body>
</html>
"""


def save_html_report(body: str, output_dir: str = "output") -> str:
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    path = os.path.join(output_dir, f"report_{ts}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(_HTML_FRAME.format(css=_CSS, body=body))
    return path


def build_dungeon_html(
    deltas: list[AbilityDelta],
    dungeon_name: str,
    bracket: int,
    your_dps: float,
    top_n_dps: float,
    top_n: int,
    your_name: str,
) -> str:
    dps_gap = ((your_dps - top_n_dps) / top_n_dps * 100) if top_n_dps else 0.0
    gap_cls = "pos" if dps_gap >= 0 else "neg"
    rows = "".join(
        f"<tr>"
        f"<td>{d.ability_name}</td>"
        f"<td>{d.your_casts}</td>"
        f"<td>{d.top_n_avg:.1f}</td>"
        f"<td class=\"{'pos' if d.cast_delta > 0 else ('neg' if d.cast_delta < 0 else 'neu')}\">{d.cast_delta:+.1f}</td>"
        f"<td>{d.your_gcd_pct:.1f}%</td>"
        f"<td>{d.top_n_gcd_pct:.1f}%</td>"
        f"<td class=\"{'pos' if d.gcd_delta > 0 else ('neg' if d.gcd_delta < 0 else 'neu')}\">{d.gcd_delta:+.1f}%</td>"
        f"</tr>"
        for d in deltas
    )
    return (
        f"<h1>{your_name} — {dungeon_name} +{bracket}</h1>"
        f"<p class=\"meta\">Your DPS: {your_dps:,.0f} &nbsp;|&nbsp; "
        f"Top {top_n} avg: {top_n_dps:,.0f} &nbsp;|&nbsp; "
        f"Gap: <span class=\"{gap_cls}\">{dps_gap:+.1f}%</span></p>"
        f"<h2>Ability Breakdown</h2>"
        f"<table><thead><tr>"
        f"<th>Ability</th><th>Your Casts</th><th>Top {top_n} Avg</th>"
        f"<th>Cast Δ</th><th>Your GCD%</th><th>Top {top_n} GCD%</th><th>GCD Δ</th>"
        f"</tr></thead><tbody>{rows}</tbody></table>"
    )


def build_overview_html(
    results: list[dict],
    your_name: str,
    bracket: int,
    top_n: int,
) -> str:
    cards = "".join(
        f"<div class=\"card\">"
        f"<div class=\"label\">{r['dungeon']}</div>"
        f"<div class=\"value\">+{r['bracket']} &nbsp; {r['fight_duration_s']}s</div>"
        f"<div class=\"meta\">Top {r['top_n']} avg: {r['top_n_dps']:,.0f} dps</div>"
        f"</div>"
        for r in results
    )
    return (
        f"<h1>{your_name} — Season Overview</h1>"
        f"<p class=\"meta\">Bracket +{bracket} &nbsp;|&nbsp; Comparing vs Top {top_n}</p>"
        f"<h2>Dungeons Run</h2>"
        f"<div class=\"cards\">{cards}</div>"
    )


def build_compare_html(
    your_casts: dict[int, int],
    their_casts: dict[int, int],
    ability_names: dict[int, str],
    your_name: str,
    their_name: str,
    dungeon_name: str,
    bracket: int,
) -> str:
    all_ids = sorted(
        set(your_casts) | set(their_casts),
        key=lambda i: your_casts.get(i, 0) + their_casts.get(i, 0),
        reverse=True,
    )

    def _rows(casts: dict[int, int], other: dict[int, int], is_you: bool) -> str:
        out = ""
        for aid in all_ids:
            mine = casts.get(aid, 0)
            theirs = other.get(aid, 0)
            diff = mine - theirs
            cls = "pos" if diff > 0 else ("neg" if diff < 0 else "neu")
            out += (
                f"<div style=\"display:flex;justify-content:space-between;padding:5px 0;"
                f"border-bottom:1px solid #1c1c1c\">"
                f"<span>{ability_names.get(aid, str(aid))}</span>"
                f"<span class=\"{cls if is_you else 'neu'}\">{mine}</span>"
                f"</div>"
            )
        return out

    return (
        f"<h1>1v1 — {your_name} vs {their_name}</h1>"
        f"<p class=\"meta\">{dungeon_name} +{bracket}</p>"
        f"<div class=\"split\">"
        f"<div class=\"player-col\"><h3>{your_name}</h3>{_rows(your_casts, their_casts, True)}</div>"
        f"<div class=\"player-col\"><h3>{their_name}</h3>{_rows(their_casts, your_casts, False)}</div>"
        f"</div>"
    )
