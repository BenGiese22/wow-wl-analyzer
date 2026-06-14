import json
from src.client import query
from src.queries import GET_CAST_EVENTS, GET_REPORT_MASTER_DATA


def fetch_cast_counts(
    token: str,
    report_code: str,
    fight_id: int,
    source_id: int,
    fight_start: float,
    fight_end: float,
) -> dict[int, int]:
    counts: dict[int, int] = {}
    start = fight_start
    while True:
        data = query(token, GET_CAST_EVENTS, {
            "code": report_code,
            "fightIDs": [fight_id],
            "sourceID": source_id,
            "startTime": start,
            "endTime": fight_end,
        })
        events_blob = data["reportData"]["report"]["events"]
        raw = events_blob["data"]
        if isinstance(raw, str):
            raw = json.loads(raw)
        for event in raw:
            if event.get("type") == "cast":
                aid = event.get("abilityGameID", 0)
                counts[aid] = counts.get(aid, 0) + 1
        next_ts = events_blob.get("nextPageTimestamp")
        if next_ts is None:
            break
        start = float(next_ts)
    return counts


def find_actor_id(token: str, report_code: str, player_name: str) -> int:
    data = query(token, GET_REPORT_MASTER_DATA, {"code": report_code})
    actors = data["reportData"]["report"]["masterData"]["actors"]
    for actor in actors:
        if actor["name"].lower() == player_name.lower():
            return actor["id"]
    raise ValueError(f"Player '{player_name}' not found in report '{report_code}'.")


def extract_ability_names(master_data: dict) -> dict[int, str]:
    return {
        int(a["gameID"]): a["name"]
        for a in master_data.get("abilities", [])
    }
