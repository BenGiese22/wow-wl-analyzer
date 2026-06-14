# tests/test_events.py
import json
import pytest
from unittest.mock import patch
from src.events import fetch_cast_counts, find_actor_id, extract_ability_names


def _events_response(events: list, next_ts=None):
    return {
        "reportData": {
            "report": {
                "events": {
                    "data": json.dumps(events),
                    "nextPageTimestamp": next_ts,
                }
            }
        }
    }


def _master_response(actors: list, abilities: list = None):
    return {
        "reportData": {
            "report": {
                "masterData": {
                    "actors": actors,
                    "abilities": abilities or [],
                }
            }
        }
    }


def _patch_query(side_effect=None, return_value=None):
    if side_effect:
        return patch("src.events.query", side_effect=side_effect)
    return patch("src.events.query", return_value=return_value)


def test_fetch_cast_counts_single_page():
    events = [
        {"type": "cast", "abilityGameID": 30451, "sourceID": 1},
        {"type": "cast", "abilityGameID": 30451, "sourceID": 1},
        {"type": "cast", "abilityGameID": 79683, "sourceID": 1},
        {"type": "damage", "abilityGameID": 30451, "sourceID": 1},  # ignored
    ]
    with _patch_query(return_value=_events_response(events)):
        counts = fetch_cast_counts("tok", "abc", 1, 1, 0.0, 9999.0)
    assert counts == {30451: 2, 79683: 1}


def test_fetch_cast_counts_paginates():
    page1_events = [{"type": "cast", "abilityGameID": 30451, "sourceID": 1}]
    page2_events = [{"type": "cast", "abilityGameID": 30451, "sourceID": 1},
                    {"type": "cast", "abilityGameID": 79683, "sourceID": 1}]
    responses = [
        _events_response(page1_events, next_ts=5000.0),
        _events_response(page2_events, next_ts=None),
    ]
    with _patch_query(side_effect=responses):
        counts = fetch_cast_counts("tok", "abc", 1, 1, 0.0, 9999.0)
    assert counts == {30451: 2, 79683: 1}


def test_fetch_cast_counts_empty():
    with _patch_query(return_value=_events_response([])):
        counts = fetch_cast_counts("tok", "abc", 1, 1, 0.0, 9999.0)
    assert counts == {}


def test_find_actor_id_found():
    actors = [{"id": 10, "name": "Bêngi", "subType": "Mage"},
               {"id": 11, "name": "Tankman", "subType": "Warrior"}]
    with _patch_query(return_value=_master_response(actors)):
        actor_id = find_actor_id("tok", "abc", "Bêngi")
    assert actor_id == 10


def test_find_actor_id_case_insensitive():
    actors = [{"id": 5, "name": "Playerone", "subType": "Mage"}]
    with _patch_query(return_value=_master_response(actors)):
        actor_id = find_actor_id("tok", "abc", "playerone")
    assert actor_id == 5


def test_find_actor_id_not_found():
    with _patch_query(return_value=_master_response([])):
        with pytest.raises(ValueError, match="not found"):
            find_actor_id("tok", "abc", "Ghost")


def test_extract_ability_names():
    master_data = {
        "abilities": [
            {"gameID": 30451, "name": "Arcane Blast"},
            {"gameID": 79683, "name": "Arcane Missiles"},
        ]
    }
    names = extract_ability_names(master_data)
    assert names == {30451: "Arcane Blast", 79683: "Arcane Missiles"}


def test_extract_ability_names_empty():
    assert extract_ability_names({}) == {}
    assert extract_ability_names({"abilities": []}) == {}
