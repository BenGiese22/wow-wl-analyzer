import json
from src.client import query
from src.queries import GET_CHARACTER_RANKINGS


def fetch_top_rankings(
    token: str,
    encounter_id: int,
    class_name: str,
    spec_name: str,
    region: str,
    bracket: int,
    top_n: int,
) -> list[dict]:
    results: list[dict] = []
    page = 1
    while len(results) < top_n:
        data = query(token, GET_CHARACTER_RANKINGS, {
            "encounterID": encounter_id,
            "className": class_name,
            "specName": spec_name,
            "serverRegion": region,
            "bracket": bracket,
            "page": page,
        })
        raw = data["worldData"]["encounter"]["characterRankings"]
        if isinstance(raw, str):
            raw = json.loads(raw)
        rankings = raw.get("rankings", [])
        if not rankings:
            break
        for r in rankings:
            if len(results) >= top_n:
                break
            results.append({
                "name": r["name"],
                "server": r.get("server", {}).get("name", ""),
                "amount": r["amount"],
                "report_code": r["report"]["code"],
                "fight_id": r["report"]["fightID"],
                "duration": r.get("duration", 0),
            })
        if not raw.get("hasMorePages", False):
            break
        page += 1
    return results
