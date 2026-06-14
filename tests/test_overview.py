# tests/test_overview.py
import json
import pytest
from unittest.mock import patch, MagicMock


def _rankings_json(avg_dps=271044.0):
    entry = {
        "name": "Playerone", "server": {"name": "Illidan"},
        "amount": avg_dps, "duration": 2100000,
        "report": {"code": "xXyYzZ", "fightID": 1, "startTime": 0}
    }
    return json.dumps({"rankings": [entry], "page": 1, "hasMorePages": False, "count": 1})


def _report_fights(encounter_id=12874, keystone=18):
    return {
        "reportData": {
            "report": {
                "startTime": 0, "endTime": 9999999,
                "region": {"compactName": "US"},
                "fights": [{
                    "id": 3, "encounterID": encounter_id, "name": "Maisara Caverns",
                    "keystoneLevel": keystone, "startTime": 0, "endTime": 134000, "kill": True
                }],
                "masterData": {
                    "actors": [{"id": 42, "name": "Bêngi", "subType": "Mage"}],
                    "abilities": [{"gameID": 30451, "name": "Arcane Blast"}]
                }
            }
        }
    }


def test_overview_prints_dungeon_found():
    env = {
        "WCL_CLIENT_ID": "id", "WCL_CLIENT_SECRET": "sec",
        "CHARACTER_NAME": "Bêngi", "CHARACTER_REALM": "Illidan",
        "CHARACTER_REGION": "US", "CHARACTER_CLASS": "Mage", "CHARACTER_SPEC": "Arcane",
        "TOP_N_PARSES": "1", "DEFAULT_BRACKET": "18",
    }
    rankings_resp = {"worldData": {"encounter": {"characterRankings": _rankings_json()}}}

    with patch.dict("os.environ", env), \
         patch("src.auth.get_access_token", return_value="tok"), \
         patch("src.client.query", return_value=_report_fights()), \
         patch("src.rankings.query", return_value=rankings_resp), \
         patch("src.report.console"), \
         patch("src.report.save_html_report", return_value="output/report.html"), \
         patch("src.report.print_overview_results") as mock_print:
        import importlib, analyze
        importlib.reload(analyze)
        args = MagicMock()
        args.report = "aAbBcC"
        args.top = 1
        args.bracket = 18
        analyze.cmd_overview(args)
    mock_print.assert_called_once()
    results = mock_print.call_args[0][0]
    assert len(results) == 1
    assert results[0]["dungeon"] == "Maisara Caverns"


def test_overview_skips_wrong_bracket():
    env = {
        "WCL_CLIENT_ID": "id", "WCL_CLIENT_SECRET": "sec",
        "CHARACTER_NAME": "Bêngi", "CHARACTER_REALM": "Illidan",
        "CHARACTER_REGION": "US", "CHARACTER_CLASS": "Mage", "CHARACTER_SPEC": "Arcane",
        "TOP_N_PARSES": "1", "DEFAULT_BRACKET": "18",
    }
    wrong_bracket_fights = _report_fights(encounter_id=12874, keystone=19)

    with patch.dict("os.environ", env), \
         patch("src.auth.get_access_token", return_value="tok"), \
         patch("src.client.query", return_value=wrong_bracket_fights), \
         patch("src.report.console"), \
         patch("src.report.print_overview_results") as mock_print:
        import importlib, analyze
        importlib.reload(analyze)
        args = MagicMock()
        args.report = "aAbBcC"
        args.top = 1
        args.bracket = 18
        analyze.cmd_overview(args)
    mock_print.assert_called_once()
    assert mock_print.call_args[0][0] == []
