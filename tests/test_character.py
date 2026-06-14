# tests/test_character.py
import pytest
from unittest.mock import patch
from src.character import lookup_character, get_specs_for_class


def _patch_query(return_value):
    return patch("src.character.query", return_value=return_value)


def test_lookup_character_success():
    mock_data = {
        "characterData": {
            "character": {"id": 1, "name": "Bêngi", "classID": 4}
        }
    }
    with _patch_query(mock_data):
        result = lookup_character("tok", "Bêngi", "Illidan", "US")
    assert result["name"] == "Bêngi"
    assert result["class_name"] == "Mage"
    assert result["class_id"] == 4


def test_lookup_character_sends_lowercase_slug():
    mock_data = {"characterData": {"character": {"id": 1, "name": "X", "classID": 4}}}
    with _patch_query(mock_data) as mock_q:
        lookup_character("tok", "X", "Illidan", "US")
    variables = mock_q.call_args[0][2]
    assert variables["serverSlug"] == "illidan"
    assert variables["serverRegion"] == "US"


def test_lookup_character_not_found():
    mock_data = {"characterData": {"character": None}}
    with _patch_query(mock_data):
        with pytest.raises(ValueError, match="not found"):
            lookup_character("tok", "Ghost", "Illidan", "US")


def test_lookup_character_utf8_name():
    mock_data = {"characterData": {"character": {"id": 2, "name": "Æthon", "classID": 11}}}
    with _patch_query(mock_data):
        result = lookup_character("tok", "Æthon", "Stormrage", "US")
    assert result["name"] == "Æthon"
    assert result["class_name"] == "Warrior"


def test_get_specs_for_mage():
    specs = get_specs_for_class("Mage")
    assert specs == ["Arcane", "Fire", "Frost"]


def test_get_specs_for_unknown_class():
    specs = get_specs_for_class("NotAClass")
    assert specs == []
