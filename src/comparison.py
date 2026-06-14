from dataclasses import dataclass


@dataclass
class AbilityDelta:
    ability_id: int
    ability_name: str
    your_casts: int
    top_n_avg: float
    cast_delta: float
    your_gcd_pct: float
    top_n_gcd_pct: float
    gcd_delta: float


def compute_comparison(
    player_casts: dict[int, int],
    competitor_casts: list[dict[int, int]],
    ability_names: dict[int, str],
) -> list[AbilityDelta]:
    if not competitor_casts:
        raise ValueError("competitor_casts must not be empty")

    all_ids = set(player_casts.keys())
    for c in competitor_casts:
        all_ids.update(c.keys())

    player_total = sum(player_casts.values()) or 1
    comp_totals = [sum(c.values()) or 1 for c in competitor_casts]

    deltas: list[AbilityDelta] = []
    for ability_id in all_ids:
        your_casts = player_casts.get(ability_id, 0)
        comp_counts = [c.get(ability_id, 0) for c in competitor_casts]
        top_n_avg = sum(comp_counts) / len(comp_counts)

        your_gcd_pct = (your_casts / player_total) * 100
        comp_gcd_pcts = [
            (competitor_casts[i].get(ability_id, 0) / comp_totals[i]) * 100
            for i in range(len(competitor_casts))
        ]
        top_n_gcd_pct = sum(comp_gcd_pcts) / len(comp_gcd_pcts)

        deltas.append(AbilityDelta(
            ability_id=ability_id,
            ability_name=ability_names.get(ability_id, str(ability_id)),
            your_casts=your_casts,
            top_n_avg=round(top_n_avg, 1),
            cast_delta=round(your_casts - top_n_avg, 1),
            your_gcd_pct=round(your_gcd_pct, 1),
            top_n_gcd_pct=round(top_n_gcd_pct, 1),
            gcd_delta=round(your_gcd_pct - top_n_gcd_pct, 1),
        ))

    deltas.sort(key=lambda d: abs(d.gcd_delta), reverse=True)
    return deltas
