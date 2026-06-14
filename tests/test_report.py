# tests/test_report.py
import os
import pytest
from io import StringIO
from unittest.mock import patch
from src.comparison import AbilityDelta
from src.report import print_dungeon_table, print_overview_results, print_compare_table

_DELTAS = [
    AbilityDelta(30451, "Arcane Blast", 142, 126.0, 16.0, 38.2, 33.9, 4.3),
    AbilityDelta(342130, "Arcane Pulse", 21, 38.0, -17.0, 5.6, 10.2, -4.6),
]


def _capture(fn, *args, **kwargs) -> str:
    buf = StringIO()
    with patch("src.report.console") as mock_console:
        printed = []
        mock_console.print.side_effect = lambda *a, **kw: printed.append(str(a))
        fn(*args, **kwargs)
    return " ".join(printed)


def test_print_dungeon_table_contains_ability_names():
    buf = StringIO()
    with patch("src.report.console") as mc:
        calls = []
        mc.print.side_effect = lambda *a, **kw: calls.append(a)
        print_dungeon_table(_DELTAS, "Maisara Caverns", 18, 245312.0, 271044.0, 10)
    all_output = " ".join(str(c) for c in calls)
    assert "Arcane Blast" in all_output
    assert "Arcane Pulse" in all_output


def test_print_overview_results_contains_dungeon_names():
    results = [
        {"dungeon": "Maisara Caverns", "bracket": 18, "top_n_dps": 271044.0, "top_n": 10, "fight_duration_s": 134},
        {"dungeon": "Windrunner Spire", "bracket": 18, "top_n_dps": 289000.0, "top_n": 10, "fight_duration_s": 119},
    ]
    with patch("src.report.console") as mc:
        calls = []
        mc.print.side_effect = lambda *a, **kw: calls.append(a)
        print_overview_results(results)
    all_output = " ".join(str(c) for c in calls)
    assert "Maisara Caverns" in all_output
    assert "Windrunner Spire" in all_output


def test_print_compare_table_shows_both_players():
    your_casts = {30451: 142}
    their_casts = {30451: 126}
    names = {30451: "Arcane Blast"}
    with patch("src.report.console") as mc:
        calls = []
        mc.print.side_effect = lambda *a, **kw: calls.append(a)
        print_compare_table(your_casts, their_casts, names, "Bêngi", "Playerone")
    all_output = " ".join(str(c) for c in calls)
    assert "Bêngi" in all_output
    assert "Playerone" in all_output
    assert "Arcane Blast" in all_output
