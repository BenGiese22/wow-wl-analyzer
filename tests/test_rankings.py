# tests/test_rankings.py
import json
import pytest
from unittest.mock import patch, call
from src.rankings import fetch_top_rankings

_RANKING_ENTRY = {
    "name": "Playerone",
    "server": {"name": "Illidan", "region": "US"},
    "amount": 312000.0,
    "duration": 2134567,
    "report": {"code": "aAbBcC", "fightID": 3, "startTime": 1749123456000},
}


def _rankings_response(rankings, has_more=False, page=1):
    raw = json.dumps({"rankings": rankings, "page": page, "hasMorePages": has_more, "count": len(rankings)})
    return {"worldData": {"encounter": {"characterRankings": raw}}}


def _patch_query(side_effect=None, return_value=None):
    if side_effect:
        return patch("src.rankings.query", side_effect=side_effect)
    return patch("src.rankings.query", return_value=return_value)


def test_fetch_top_rankings_returns_parsed_list():
    with _patch_query(return_value=_rankings_response([_RANKING_ENTRY])):
        results = fetch_top_rankings("tok", 12874, "Mage", "Arcane", "US", 18, 1)
    assert len(results) == 1
    assert results[0]["name"] == "Playerone"
    assert results[0]["amount"] == 312000.0
    assert results[0]["report_code"] == "aAbBcC"
    assert results[0]["fight_id"] == 3


def test_fetch_top_rankings_respects_top_n():
    entries = [dict(_RANKING_ENTRY, name=f"Player{i}") for i in range(5)]
    with _patch_query(return_value=_rankings_response(entries)):
        results = fetch_top_rankings("tok", 12874, "Mage", "Arcane", "US", 18, top_n=3)
    assert len(results) == 3


def test_fetch_top_rankings_paginates():
    page1 = [dict(_RANKING_ENTRY, name=f"P{i}") for i in range(2)]
    page2 = [dict(_RANKING_ENTRY, name=f"Q{i}") for i in range(2)]
    responses = [
        _rankings_response(page1, has_more=True, page=1),
        _rankings_response(page2, has_more=False, page=2),
    ]
    with _patch_query(side_effect=responses):
        results = fetch_top_rankings("tok", 12874, "Mage", "Arcane", "US", 18, top_n=4)
    assert len(results) == 4
    assert results[0]["name"] == "P0"
    assert results[2]["name"] == "Q0"


def test_fetch_top_rankings_empty():
    with _patch_query(return_value=_rankings_response([])):
        results = fetch_top_rankings("tok", 12874, "Mage", "Arcane", "US", 18, top_n=10)
    assert results == []
