# tests/test_comparison.py
import pytest
from src.comparison import AbilityDelta, compute_comparison

_NAMES = {30451: "Arcane Blast", 342130: "Arcane Pulse", 79683: "Arcane Missiles"}


def test_basic_delta():
    player = {30451: 142, 342130: 21}
    competitors = [{30451: 126, 342130: 38}]
    result = compute_comparison(player, competitors, _NAMES)
    ab = next(d for d in result if d.ability_id == 30451)
    assert ab.your_casts == 142
    assert ab.top_n_avg == 126.0
    assert ab.cast_delta == 16.0


def test_gcd_pct_normalized():
    # Player: 100 casts total (80 AB, 20 AP)
    # Competitor: 100 casts total (50 AB, 50 AP)
    player = {30451: 80, 342130: 20}
    competitors = [{30451: 50, 342130: 50}]
    result = compute_comparison(player, competitors, _NAMES)
    ab = next(d for d in result if d.ability_id == 30451)
    assert ab.your_gcd_pct == 80.0
    assert ab.top_n_gcd_pct == 50.0
    assert ab.gcd_delta == 30.0


def test_sorted_by_abs_gcd_delta_descending():
    # AB: gcd_delta = +30%, AP: gcd_delta = -30%, AM: gcd_delta = 0%
    player = {30451: 80, 342130: 10, 79683: 10}
    competitors = [{30451: 50, 342130: 40, 79683: 10}]
    result = compute_comparison(player, competitors, _NAMES)
    assert abs(result[0].gcd_delta) >= abs(result[1].gcd_delta)
    assert abs(result[1].gcd_delta) >= abs(result[2].gcd_delta)


def test_ability_present_in_competitor_but_not_player():
    player = {30451: 100}
    competitors = [{30451: 80, 342130: 20}]
    result = compute_comparison(player, competitors, _NAMES)
    ap = next(d for d in result if d.ability_id == 342130)
    assert ap.your_casts == 0
    assert ap.top_n_avg == 20.0
    assert ap.gcd_delta < 0


def test_multiple_competitors_averaged():
    player = {30451: 100}
    competitors = [{30451: 80}, {30451: 120}]
    result = compute_comparison(player, competitors, _NAMES)
    ab = next(d for d in result if d.ability_id == 30451)
    assert ab.top_n_avg == 100.0
    assert ab.cast_delta == 0.0


def test_unknown_ability_uses_id_as_name():
    player = {99999: 5}
    competitors = [{99999: 5}]
    result = compute_comparison(player, competitors, {})
    assert result[0].ability_name == "99999"


def test_empty_competitors_raises():
    with pytest.raises(ValueError, match="empty"):
        compute_comparison({30451: 10}, [], _NAMES)
