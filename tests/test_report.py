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


import tempfile
from src.report import save_html_report, build_dungeon_html, build_overview_html, build_compare_html


def test_save_html_report_creates_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = save_html_report("<p>test</p>", output_dir=tmpdir)
        assert path.endswith(".html")
        assert os.path.exists(path)


def test_build_dungeon_html_contains_ability_names():
    html = build_dungeon_html(_DELTAS, "Maisara Caverns", 18, 245312.0, 271044.0, 10, "Bêngi")
    assert "Arcane Blast" in html
    assert "Arcane Pulse" in html
    assert "Maisara Caverns" in html


def test_build_overview_html_contains_dungeons():
    results = [{"dungeon": "Maisara Caverns", "bracket": 18, "top_n_dps": 271044.0, "top_n": 10, "fight_duration_s": 134}]
    html = build_overview_html(results, "Bêngi", 18, 10)
    assert "Maisara Caverns" in html
    assert "Bêngi" in html


def test_build_compare_html_contains_both_names():
    html = build_compare_html(
        {30451: 142}, {30451: 126},
        {30451: "Arcane Blast"},
        "Bêngi", "Playerone",
        "Maisara Caverns", 18,
    )
    assert "Bêngi" in html
    assert "Playerone" in html
    assert "Arcane Blast" in html


def test_html_report_is_utf8():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = save_html_report("<p>Bêngi</p>", output_dir=tmpdir)
        content = open(path, encoding="utf-8").read()
        assert "Bêngi" in content
