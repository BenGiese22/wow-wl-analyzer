# tests/test_dungeon.py
import json
import pytest
from unittest.mock import patch, MagicMock, call

_ENV = {
    "WCL_CLIENT_ID": "id", "WCL_CLIENT_SECRET": "sec",
    "CHARACTER_NAME": "Bêngi", "CHARACTER_REALM": "Illidan",
    "CHARACTER_REGION": "US", "CHARACTER_CLASS": "Mage", "CHARACTER_SPEC": "Arcane",
    "TOP_N_PARSES": "1", "DEFAULT_BRACKET": "18",
}


def _fights_resp(encounter_id=12874, keystone=18):
    return {
        "reportData": {
            "report": {
                "startTime": 0, "endTime": 999999,
                "region": {"compactName": "US"},
                "fights": [{
                    "id": 3, "encounterID": encounter_id,
                    "keystoneLevel": keystone, "startTime": 0, "endTime": 134000, "kill": True
                }],
                "masterData": {
                    "actors": [{"id": 42, "name": "Bêngi", "subType": "Mage"}],
                    "abilities": [{"gameID": 30451, "name": "Arcane Blast"},
                                  {"gameID": 342130, "name": "Arcane Pulse"}],
                }
            }
        }
    }


def _rankings_resp():
    entry = {"name": "P1", "server": {"name": "Illidan"}, "amount": 310000.0,
             "duration": 2100000, "report": {"code": "xX", "fightID": 1, "startTime": 0}}
    raw = json.dumps({"rankings": [entry], "page": 1, "hasMorePages": False, "count": 1})
    return {"worldData": {"encounter": {"characterRankings": raw}}}


def _cast_events_resp(casts: dict):
    events = [{"type": "cast", "abilityGameID": aid, "sourceID": 1}
              for aid, count in casts.items() for _ in range(count)]
    return {"reportData": {"report": {"events": {"data": json.dumps(events), "nextPageTimestamp": None}}}}


def _master_resp():
    return {"reportData": {"report": {"masterData": {
        "actors": [{"id": 99, "name": "P1", "subType": "Mage"}],
        "abilities": [{"gameID": 30451, "name": "Arcane Blast"}]
    }}}}


def test_dungeon_calls_comparison_and_prints():
    player_casts = {30451: 142, 342130: 21}
    comp_casts = {30451: 126, 342130: 38}

    with patch.dict("os.environ", _ENV), \
         patch("src.auth.get_access_token", return_value="tok"), \
         patch("src.client.query", return_value=_fights_resp()), \
         patch("src.rankings.query", return_value=_rankings_resp()), \
         patch("src.events.query", side_effect=[_cast_events_resp(player_casts), _master_resp(), _cast_events_resp(comp_casts)]), \
         patch("src.report.console"), \
         patch("src.report.print_dungeon_table") as mock_print, \
         patch("src.report.save_html_report", return_value="output/r.html"):
        import importlib, analyze
        importlib.reload(analyze)
        args = MagicMock()
        args.report = "aAbBcC"
        args.dungeon = "Maisara Caverns"
        args.bracket = 18
        args.top = 1
        analyze.cmd_dungeon(args)

    mock_print.assert_called_once()
    deltas = mock_print.call_args[0][0]
    ids = {d.ability_id for d in deltas}
    assert 30451 in ids
    assert 342130 in ids


def test_dungeon_no_matching_fight_exits():
    wrong_bracket = _fights_resp(keystone=20)
    with patch.dict("os.environ", _ENV), \
         patch("src.auth.get_access_token", return_value="tok"), \
         patch("src.client.query", return_value=wrong_bracket), \
         patch("src.report.console"), \
         pytest.raises(SystemExit):
        import importlib, analyze
        importlib.reload(analyze)
        args = MagicMock()
        args.report = "aAbBcC"
        args.dungeon = "Maisara Caverns"
        args.bracket = 18
        args.top = 1
        analyze.cmd_dungeon(args)
