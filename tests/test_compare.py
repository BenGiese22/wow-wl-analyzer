# tests/test_compare.py
import json
import pytest
from unittest.mock import patch, MagicMock

_ENV = {
    "WCL_CLIENT_ID": "id", "WCL_CLIENT_SECRET": "sec",
    "CHARACTER_NAME": "Bêngi", "CHARACTER_REALM": "Illidan",
    "CHARACTER_REGION": "US", "CHARACTER_CLASS": "Mage", "CHARACTER_SPEC": "Arcane",
    "TOP_N_PARSES": "1", "DEFAULT_BRACKET": "18",
}


def _master_resp(char_name="Bêngi", actor_id=42):
    return {"reportData": {"report": {"masterData": {
        "actors": [{"id": actor_id, "name": char_name, "subType": "Mage"}],
        "abilities": [{"gameID": 30451, "name": "Arcane Blast"},
                      {"gameID": 342130, "name": "Arcane Pulse"}],
    }}}}


def _cast_resp(casts: dict):
    events = [{"type": "cast", "abilityGameID": aid, "sourceID": 1}
              for aid, n in casts.items() for _ in range(n)]
    return {"reportData": {"report": {"events": {
        "data": json.dumps(events), "nextPageTimestamp": None
    }}}}


def test_compare_fetches_both_players_and_prints():
    my_casts = {30451: 142, 342130: 21}
    their_casts = {30451: 126, 342130: 38}

    side_effects = [
        _master_resp("Bêngi", 42),
        _cast_resp(my_casts),
        _master_resp("Playerone", 99),
        _cast_resp(their_casts),
    ]

    with patch.dict("os.environ", _ENV), \
         patch("src.auth.get_access_token", return_value="tok"), \
         patch("src.events.query", side_effect=side_effects), \
         patch("src.report.console"), \
         patch("src.report.print_compare_table") as mock_print, \
         patch("src.report.save_html_report", return_value="output/r.html"):
        import importlib, analyze
        importlib.reload(analyze)
        args = MagicMock()
        args.report = "aAbBcC"
        args.fight = 3
        args.vs = "xXyYzZ"
        args.vs_fight = 1
        analyze.cmd_compare(args)

    mock_print.assert_called_once()
    call_args = mock_print.call_args[0]
    your_casts_arg, their_casts_arg = call_args[0], call_args[1]
    assert your_casts_arg.get(30451) == 142
    assert their_casts_arg.get(342130) == 38
