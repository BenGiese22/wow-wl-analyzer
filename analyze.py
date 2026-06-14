#!/usr/bin/env python3
"""wow-wl-analyzer — WoW Mythic+ cast comparison tool."""
import argparse
import getpass
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(encoding="utf-8")


def _require_env(key: str) -> str:
    val = os.getenv(key)
    if not val:
        print(f"Missing {key}. Run: python analyze.py setup", file=sys.stderr)
        sys.exit(1)
    return val


def cmd_setup(args, env_path: str = ".env") -> None:
    from src.auth import get_access_token
    from src.character import lookup_character, get_specs_for_class
    from src.report import console

    console.print("\n[bold]wow-wl-analyzer setup[/bold]")
    console.print("─" * 52)
    console.print("\nCreate a WCL API client at:")
    console.print("  https://www.warcraftlogs.com/api/clients/\n")

    client_id = input("WCL Client ID: ").strip()
    client_secret = getpass.getpass("WCL Client Secret: ").strip()

    try:
        token = get_access_token(client_id, client_secret)
        console.print("[green]✓ Credentials validated[/green]")
    except ValueError as e:
        console.print(f"[red]✗ {e}[/red]")
        sys.exit(1)

    print()
    char_name = input("Character name: ").strip()
    realm = input("Realm: ").strip()
    region = (input("Region [US]: ").strip() or "US").upper()

    try:
        char = lookup_character(token, char_name, realm, region)
        console.print(f"[green]✓ Found: {char['name']}-{realm} ({char['class_name']})[/green]")
    except ValueError as e:
        console.print(f"[red]✗ {e}[/red]")
        sys.exit(1)

    specs = get_specs_for_class(char["class_name"])
    spec_menu = ", ".join(f"[{i + 1}] {s}" for i, s in enumerate(specs))
    console.print(f"Specs: {spec_menu}")
    spec_input = (input("Which spec? [1]: ").strip() or "1")
    try:
        spec_name = specs[int(spec_input) - 1]
    except (ValueError, IndexError):
        console.print("[red]Invalid spec choice[/red]")
        sys.exit(1)

    print()
    top_n = int(input("Top N parses [10]: ").strip() or "10")
    bracket = int(input("Default keystone bracket [18]: ").strip() or "18")

    content = (
        "# WCL API credentials\n"
        f"WCL_CLIENT_ID={client_id}\n"
        f"WCL_CLIENT_SECRET={client_secret}\n\n"
        "# Your character\n"
        f"CHARACTER_NAME={char_name}\n"
        f"CHARACTER_REALM={realm}\n"
        f"CHARACTER_REGION={region}\n"
        f"CHARACTER_CLASS={char['class_name']}\n"
        f"CHARACTER_SPEC={spec_name}\n\n"
        "# Analysis defaults\n"
        f"TOP_N_PARSES={top_n}\n"
        f"DEFAULT_BRACKET={bracket}\n"
    )
    Path(env_path).write_text(content, encoding="utf-8")
    console.print(f"\n[green]✓ Config saved to {env_path}[/green]")
    console.print("\nYou're set. Try:")
    console.print(f"  python analyze.py overview --report <code>")
    console.print(f"  python analyze.py dungeon --report <code> --dungeon \"Maisara Caverns\" --bracket {bracket}")
    console.print(f"  python analyze.py compare --report <code> --fight <id> --vs <report> --vs-fight <id>")


def cmd_overview(args) -> None:
    from src.auth import get_access_token
    from src.client import query as wcl_query
    from src.constants import DUNGEONS
    from src.queries import GET_REPORT_FIGHTS
    from src.rankings import fetch_top_rankings
    from src import report as rpt

    client_id = _require_env("WCL_CLIENT_ID")
    client_secret = _require_env("WCL_CLIENT_SECRET")
    class_name = _require_env("CHARACTER_CLASS")
    spec_name = _require_env("CHARACTER_SPEC")
    region = os.getenv("CHARACTER_REGION", "US")
    top_n = args.top or int(os.getenv("TOP_N_PARSES", "10"))
    bracket = args.bracket or int(os.getenv("DEFAULT_BRACKET", "18"))

    token = get_access_token(client_id, client_secret)
    data = wcl_query(token, GET_REPORT_FIGHTS, {"code": args.report})
    fights = data["reportData"]["report"]["fights"]

    results = []
    for dungeon_name, encounter_id in DUNGEONS.items():
        matching = [
            f for f in fights
            if f["encounterID"] == encounter_id
            and f.get("keystoneLevel") == bracket
            and f.get("kill")
        ]
        if not matching:
            continue
        best = min(matching, key=lambda f: f["endTime"] - f["startTime"])
        duration_s = round((best["endTime"] - best["startTime"]) / 1000)

        rankings = fetch_top_rankings(token, encounter_id, class_name, spec_name, region, bracket, top_n)
        if not rankings:
            continue
        top_n_dps = sum(r["amount"] for r in rankings) / len(rankings)

        results.append({
            "dungeon": dungeon_name,
            "bracket": bracket,
            "fight_id": best["id"],
            "fight_duration_s": duration_s,
            "top_n_dps": top_n_dps,
            "top_n": top_n,
            "rankings": rankings,
        })

    rpt.print_overview_results(results)
    body = rpt.build_overview_html(results, os.getenv("CHARACTER_NAME", ""), bracket, top_n)
    path = rpt.save_html_report(body)
    rpt.console.print(f"\n[dim]Full report → {path}[/dim]")


def cmd_dungeon(args) -> None:
    pass  # implemented in Task 13


def cmd_compare(args) -> None:
    pass  # implemented in Task 14


def main() -> None:
    parser = argparse.ArgumentParser(prog="analyze.py", description="WoW M+ cast analyzer")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("setup", help="Configure credentials and character")

    p_ov = sub.add_parser("overview", help="Season overview across all dungeons")
    p_ov.add_argument("--report", required=True)
    p_ov.add_argument("--top", type=int, default=None)
    p_ov.add_argument("--bracket", type=int, default=None)

    p_dn = sub.add_parser("dungeon", help="Ability-level breakdown for one dungeon")
    p_dn.add_argument("--report", required=True)
    p_dn.add_argument("--dungeon", required=True)
    p_dn.add_argument("--bracket", type=int, default=None)
    p_dn.add_argument("--top", type=int, default=None)

    p_cp = sub.add_parser("compare", help="1v1 cast-by-cast comparison")
    p_cp.add_argument("--report", required=True)
    p_cp.add_argument("--fight", type=int, required=True)
    p_cp.add_argument("--vs", required=True)
    p_cp.add_argument("--vs-fight", type=int, required=True)

    args = parser.parse_args()
    {"setup": cmd_setup, "overview": cmd_overview, "dungeon": cmd_dungeon, "compare": cmd_compare}[args.command](args)


if __name__ == "__main__":
    main()
