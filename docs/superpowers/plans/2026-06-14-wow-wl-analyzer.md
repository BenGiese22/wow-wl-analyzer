# wow-wl-analyzer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI that compares a WoW Mythic+ player's cast events against top-ranked players using the Warcraft Logs GraphQL API, outputting a terminal table and a self-contained HTML report.

**Architecture:** Seven focused modules under `src/` handle auth, API querying, data fetching, and analysis. A single `analyze.py` entry point wires them into four subcommands: `setup`, `overview`, `dungeon`, `compare`. Each module is independently testable with mocked HTTP calls.

**Tech Stack:** Python 3.10+, requests, python-dotenv, rich, pytest, unittest.mock

---

## File Map

| File | Responsibility |
|------|---------------|
| `analyze.py` | CLI entry point — argument parsing, subcommand dispatch |
| `src/__init__.py` | Empty — marks src as a package |
| `src/auth.py` | WCL OAuth2 client credentials token exchange |
| `src/client.py` | GraphQL POST wrapper with error handling |
| `src/constants.py` | Dungeon→encounterID map, class/spec ID map |
| `src/queries.py` | All GraphQL query strings as module-level constants |
| `src/character.py` | Character lookup via characterData API |
| `src/rankings.py` | Top-N parse fetching via characterRankings |
| `src/events.py` | Paginated cast event fetching, actor lookup, ability name extraction |
| `src/comparison.py` | Pure delta calculation — GCD%, cast delta, sorted by gap |
| `src/report.py` | Terminal output (rich) + HTML report generation |
| `requirements.txt` | Pinned dependencies |
| `tests/__init__.py` | Empty |
| `tests/test_auth.py` | Auth token tests |
| `tests/test_client.py` | GraphQL wrapper tests |
| `tests/test_character.py` | Character lookup tests |
| `tests/test_rankings.py` | Rankings fetch + pagination tests |
| `tests/test_events.py` | Cast event fetch + pagination + actor lookup tests |
| `tests/test_comparison.py` | Delta math, GCD% calculation, sort order tests |
| `tests/test_report.py` | Terminal output and HTML file generation tests |

---

### Task 1: Bootstrap — project skeleton and dependencies

**Files:**
- Create: `requirements.txt`
- Create: `src/__init__.py`
- Create: `tests/__init__.py`
- Modify: `.gitignore` (add `output/`)

- [ ] **Step 1: Write `requirements.txt`**

```
requests==2.32.3
python-dotenv==1.0.1
rich==13.9.4
pytest==8.3.4
```

- [ ] **Step 2: Create package markers**

```bash
mkdir -p src tests
touch src/__init__.py tests/__init__.py
```

- [ ] **Step 3: Add `output/` to `.gitignore`**

Open `.gitignore` and add after the existing `*.json` line:

```
output/
```

- [ ] **Step 4: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: all four packages install without error.

- [ ] **Step 5: Verify pytest runs**

```bash
pytest --collect-only
```

Expected output contains `no tests ran` (no errors).

- [ ] **Step 6: Commit**

```bash
git add requirements.txt src/__init__.py tests/__init__.py .gitignore
git commit -m "chore(deps): add requirements and project skeleton"
```

---

### Task 2: `src/auth.py` — OAuth token exchange

**Files:**
- Create: `src/auth.py`
- Create: `tests/test_auth.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_auth.py
import pytest
from unittest.mock import patch, MagicMock
from src.auth import get_access_token


def _mock_response(status_code: int, json_body: dict) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_body
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return resp


def test_get_access_token_success():
    mock_resp = _mock_response(200, {"access_token": "tok123", "token_type": "Bearer"})
    with patch("requests.post", return_value=mock_resp) as mock_post:
        token = get_access_token("my-id", "my-secret")
    assert token == "tok123"
    call_kwargs = mock_post.call_args[1]
    assert call_kwargs["auth"] == ("my-id", "my-secret")
    assert call_kwargs["data"] == {"grant_type": "client_credentials"}


def test_get_access_token_invalid_credentials():
    mock_resp = _mock_response(401, {"error": "unauthorized"})
    with patch("requests.post", return_value=mock_resp):
        with pytest.raises(ValueError, match="Invalid WCL credentials"):
            get_access_token("bad", "creds")


def test_get_access_token_server_error():
    mock_resp = _mock_response(500, {})
    with patch("requests.post", return_value=mock_resp):
        with pytest.raises(Exception):
            get_access_token("id", "secret")
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_auth.py -v
```

Expected: `ModuleNotFoundError: No module named 'src.auth'`

- [ ] **Step 3: Implement `src/auth.py`**

```python
import requests

_TOKEN_URL = "https://www.warcraftlogs.com/oauth/token"


def get_access_token(client_id: str, client_secret: str) -> str:
    resp = requests.post(
        _TOKEN_URL,
        auth=(client_id, client_secret),
        data={"grant_type": "client_credentials"},
        timeout=10,
    )
    if resp.status_code == 401:
        raise ValueError(
            "Invalid WCL credentials. Check your Client ID and Secret at "
            "https://www.warcraftlogs.com/api/clients/"
        )
    resp.raise_for_status()
    return resp.json()["access_token"]
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/test_auth.py -v
```

Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add src/auth.py tests/test_auth.py
git commit -m "feat(auth): add OAuth2 client credentials token exchange"
```

---

### Task 3: `src/client.py` — GraphQL request wrapper

**Files:**
- Create: `src/client.py`
- Create: `tests/test_client.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_client.py
import pytest
from unittest.mock import patch, MagicMock
from src.client import query


def _mock_resp(status: int, body: dict) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = body
    resp.raise_for_status = MagicMock()
    if status >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status}")
    return resp


def test_query_returns_data():
    resp = _mock_resp(200, {"data": {"worldData": {"expansions": []}}})
    with patch("requests.post", return_value=resp):
        result = query("tok", "{ worldData { expansions { id } } }")
    assert result == {"worldData": {"expansions": []}}


def test_query_sends_bearer_token():
    resp = _mock_resp(200, {"data": {}})
    with patch("requests.post", return_value=resp) as mock_post:
        query("mytoken", "{ rateLimitData { limitPerHour } }")
    headers = mock_post.call_args[1]["headers"]
    assert headers["Authorization"] == "Bearer mytoken"


def test_query_raises_on_graphql_errors():
    body = {"errors": [{"message": "Field not found"}, {"message": "Type mismatch"}]}
    resp = _mock_resp(200, body)
    with patch("requests.post", return_value=resp):
        with pytest.raises(RuntimeError, match="Field not found"):
            query("tok", "{ bad }")


def test_query_raises_on_http_error():
    resp = _mock_resp(500, {})
    with patch("requests.post", return_value=resp):
        with pytest.raises(Exception):
            query("tok", "{ worldData { expansions { id } } }")


def test_query_sends_variables():
    resp = _mock_resp(200, {"data": {"result": "ok"}})
    with patch("requests.post", return_value=resp) as mock_post:
        query("tok", "query ($id: Int!) { foo(id: $id) }", {"id": 42})
    payload = mock_post.call_args[1]["json"]
    assert payload["variables"] == {"id": 42}
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_client.py -v
```

Expected: `ModuleNotFoundError: No module named 'src.client'`

- [ ] **Step 3: Implement `src/client.py`**

```python
from typing import Any
import requests

_API_URL = "https://www.warcraftlogs.com/api/v2/client"


def query(token: str, gql: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
    resp = requests.post(
        _API_URL,
        json={"query": gql, "variables": variables or {}},
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    resp.raise_for_status()
    body = resp.json()
    if "errors" in body:
        msgs = "; ".join(e["message"] for e in body["errors"])
        raise RuntimeError(f"GraphQL error: {msgs}")
    return body["data"]
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/test_client.py -v
```

Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add src/client.py tests/test_client.py
git commit -m "feat(query): add GraphQL POST wrapper with error handling"
```

---

### Task 4: `src/constants.py` + `src/queries.py`

**Files:**
- Create: `src/constants.py`
- Create: `src/queries.py`

No tests for these files — they are pure data, verified indirectly by downstream tests.

- [ ] **Step 1: Create `src/constants.py`**

```python
# Midnight Season 1 M+ — encounter IDs verified via live WCL API on 2026-06-14
# Zone ID 47: "Mythic+ Season 1"
ZONE_ID = 47

DUNGEONS: dict[str, int] = {
    "Algeth'ar Academy": 112526,
    "Magisters' Terrace": 12811,
    "Maisara Caverns": 12874,
    "Nexus-Point Xenas": 12915,
    "Pit of Saron": 10658,
    "Seat of the Triumvirate": 361753,
    "Skyreach": 61209,
    "Windrunner Spire": 12805,
}

# classID → class name (verified via gameData API 2026-06-14)
CLASS_ID_TO_NAME: dict[int, str] = {
    1: "Death Knight",
    2: "Druid",
    3: "Hunter",
    4: "Mage",
    5: "Monk",
    6: "Paladin",
    7: "Priest",
    8: "Rogue",
    9: "Shaman",
    10: "Warlock",
    11: "Warrior",
    12: "Demon Hunter",
    13: "Evoker",
}

# class name → list of spec names (verified via gameData API 2026-06-14)
CLASS_SPECS: dict[str, list[str]] = {
    "Death Knight": ["Blood", "Frost", "Unholy"],
    "Druid": ["Balance", "Feral", "Guardian", "Restoration"],
    "Hunter": ["Beast Mastery", "Marksmanship", "Survival"],
    "Mage": ["Arcane", "Fire", "Frost"],
    "Monk": ["Brewmaster", "Mistweaver", "Windwalker"],
    "Paladin": ["Holy", "Protection", "Retribution"],
    "Priest": ["Discipline", "Holy", "Shadow"],
    "Rogue": ["Assassination", "Subtlety", "Outlaw"],
    "Shaman": ["Elemental", "Enhancement", "Restoration"],
    "Warlock": ["Affliction", "Demonology", "Destruction"],
    "Warrior": ["Arms", "Fury", "Protection"],
    "Demon Hunter": ["Havoc", "Vengeance", "Devourer"],
    "Evoker": ["Devastation", "Preservation", "Augmentation"],
}
```

- [ ] **Step 2: Create `src/queries.py`**

```python
VALIDATE_CREDENTIALS = """
{ rateLimitData { limitPerHour pointsSpentThisHour } }
"""

GET_CHARACTER = """
query GetCharacter($name: String!, $serverSlug: String!, $serverRegion: String!) {
  characterData {
    character(name: $name, serverSlug: $serverSlug, serverRegion: $serverRegion) {
      id
      name
      classID
    }
  }
}
"""

GET_REPORT_FIGHTS = """
query GetReportFights($code: String!) {
  reportData {
    report(code: $code) {
      startTime
      endTime
      region { compactName }
      fights(killType: Kills) {
        id
        encounterID
        name
        keystoneLevel
        startTime
        endTime
        kill
      }
      masterData(translate: true) {
        actors(type: "Player") {
          id
          name
          subType
        }
        abilities {
          gameID
          name
        }
      }
    }
  }
}
"""

GET_CHARACTER_RANKINGS = """
query GetRankings(
  $encounterID: Int!,
  $className: String!,
  $specName: String!,
  $serverRegion: String!,
  $bracket: Int!,
  $page: Int!
) {
  worldData {
    encounter(id: $encounterID) {
      characterRankings(
        className: $className
        specName: $specName
        serverRegion: $serverRegion
        difficulty: 10
        bracket: $bracket
        page: $page
        metric: dps
        includeCombatantInfo: false
        includeOtherPlayers: false
      )
    }
  }
}
"""

GET_REPORT_MASTER_DATA = """
query GetMasterData($code: String!) {
  reportData {
    report(code: $code) {
      masterData(translate: true) {
        actors(type: "Player") {
          id
          name
          subType
        }
        abilities {
          gameID
          name
        }
      }
    }
  }
}
"""

GET_CAST_EVENTS = """
query GetCastEvents(
  $code: String!,
  $fightIDs: [Int]!,
  $sourceID: Int!,
  $startTime: Float!,
  $endTime: Float!
) {
  reportData {
    report(code: $code) {
      events(
        dataType: Casts
        fightIDs: $fightIDs
        sourceID: $sourceID
        startTime: $startTime
        endTime: $endTime
        limit: 10000
        useAbilityIDs: true
      ) {
        nextPageTimestamp
        data
      }
    }
  }
}
"""

GET_DAMAGE_TABLE = """
query GetDamageTable(
  $code: String!,
  $fightIDs: [Int]!,
  $startTime: Float!,
  $endTime: Float!
) {
  reportData {
    report(code: $code) {
      table(
        dataType: DamageDone
        fightIDs: $fightIDs
        startTime: $startTime
        endTime: $endTime
        translate: true
      )
    }
  }
}
"""
```

- [ ] **Step 3: Commit**

```bash
git add src/constants.py src/queries.py
git commit -m "feat(query): add GraphQL query strings and game constants"
```

---

### Task 5: `src/character.py` — character lookup

**Files:**
- Create: `src/character.py`
- Create: `tests/test_character.py`

- [ ] **Step 1: Write failing tests**

```python
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
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_character.py -v
```

Expected: `ModuleNotFoundError: No module named 'src.character'`

- [ ] **Step 3: Implement `src/character.py`**

```python
from src.client import query
from src.constants import CLASS_ID_TO_NAME, CLASS_SPECS
from src.queries import GET_CHARACTER


def lookup_character(token: str, name: str, realm: str, region: str) -> dict:
    data = query(token, GET_CHARACTER, {
        "name": name,
        "serverSlug": realm.lower(),
        "serverRegion": region.upper(),
    })
    char = data["characterData"]["character"]
    if char is None:
        raise ValueError(
            f"Character '{name}-{realm}' ({region}) not found on WCL. "
            "Check spelling — accented characters must match exactly."
        )
    class_name = CLASS_ID_TO_NAME.get(char["classID"], f"Unknown({char['classID']})")
    return {
        "name": char["name"],
        "class_id": char["classID"],
        "class_name": class_name,
    }


def get_specs_for_class(class_name: str) -> list[str]:
    return list(CLASS_SPECS.get(class_name, []))
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/test_character.py -v
```

Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
git add src/character.py tests/test_character.py
git commit -m "feat(query): add character lookup with class/spec resolution"
```

---

### Task 6: `src/rankings.py` — top-N parse fetching

**Files:**
- Create: `src/rankings.py`
- Create: `tests/test_rankings.py`

- [ ] **Step 1: Write failing tests**

```python
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
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_rankings.py -v
```

Expected: `ModuleNotFoundError: No module named 'src.rankings'`

- [ ] **Step 3: Implement `src/rankings.py`**

```python
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
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/test_rankings.py -v
```

Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add src/rankings.py tests/test_rankings.py
git commit -m "feat(query): add top-N character rankings fetch with pagination"
```

---

### Task 7: `src/events.py` — cast events, actor lookup, ability names

**Files:**
- Create: `src/events.py`
- Create: `tests/test_events.py`

- [ ] **Step 1: Write failing tests**

```python
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
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_events.py -v
```

Expected: `ModuleNotFoundError: No module named 'src.events'`

- [ ] **Step 3: Implement `src/events.py`**

```python
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
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/test_events.py -v
```

Expected: `9 passed`

- [ ] **Step 5: Commit**

```bash
git add src/events.py tests/test_events.py
git commit -m "feat(query): add paginated cast event fetch, actor lookup, ability names"
```

---

### Task 8: `src/comparison.py` — delta calculation

**Files:**
- Create: `src/comparison.py`
- Create: `tests/test_comparison.py`

- [ ] **Step 1: Write failing tests**

```python
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
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_comparison.py -v
```

Expected: `ModuleNotFoundError: No module named 'src.comparison'`

- [ ] **Step 3: Implement `src/comparison.py`**

```python
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
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/test_comparison.py -v
```

Expected: `7 passed`

- [ ] **Step 5: Commit**

```bash
git add src/comparison.py tests/test_comparison.py
git commit -m "feat(report): add GCD-normalised cast delta computation"
```

---

### Task 9: `src/report.py` — terminal output

**Files:**
- Create: `src/report.py`
- Create: `tests/test_report.py` (terminal section)

- [ ] **Step 1: Write failing tests for terminal output**

```python
# tests/test_report.py
import os
import pytest
from io import StringIO
from unittest.mock import patch
from src.comparison import AbilityDelta
from src.report import print_dungeon_table, print_overview_results, print_compare_table

_DELTAS = [
    AbilityDelta(30451, "Arcane Blast", 142, 126.0, 16.0, 38.2, 33.9, 4.3),
    AbilityDelta(342130, "Arcane Pulse", 21, 38.0, -17.0, 5.6, 10.2, -4.6),
]


def _capture(fn, *args, **kwargs) -> str:
    buf = StringIO()
    with patch("src.report.console") as mock_console:
        printed = []
        mock_console.print.side_effect = lambda *a, **kw: printed.append(str(a))
        fn(*args, **kwargs)
    return " ".join(printed)


def test_print_dungeon_table_contains_ability_names():
    buf = StringIO()
    with patch("src.report.console") as mc:
        calls = []
        mc.print.side_effect = lambda *a, **kw: calls.append(a)
        print_dungeon_table(_DELTAS, "Maisara Caverns", 18, 245312.0, 271044.0, 10)
    all_output = " ".join(str(c) for c in calls)
    assert "Arcane Blast" in all_output
    assert "Arcane Pulse" in all_output


def test_print_overview_results_contains_dungeon_names():
    results = [
        {"dungeon": "Maisara Caverns", "bracket": 18, "top_n_dps": 271044.0, "top_n": 10, "fight_duration_s": 134},
        {"dungeon": "Windrunner Spire", "bracket": 18, "top_n_dps": 289000.0, "top_n": 10, "fight_duration_s": 119},
    ]
    with patch("src.report.console") as mc:
        calls = []
        mc.print.side_effect = lambda *a, **kw: calls.append(a)
        print_overview_results(results)
    all_output = " ".join(str(c) for c in calls)
    assert "Maisara Caverns" in all_output
    assert "Windrunner Spire" in all_output


def test_print_compare_table_shows_both_players():
    your_casts = {30451: 142}
    their_casts = {30451: 126}
    names = {30451: "Arcane Blast"}
    with patch("src.report.console") as mc:
        calls = []
        mc.print.side_effect = lambda *a, **kw: calls.append(a)
        print_compare_table(your_casts, their_casts, names, "Bêngi", "Playerone")
    all_output = " ".join(str(c) for c in calls)
    assert "Bêngi" in all_output
    assert "Playerone" in all_output
    assert "Arcane Blast" in all_output
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_report.py -v
```

Expected: `ModuleNotFoundError: No module named 'src.report'`

- [ ] **Step 3: Implement terminal output in `src/report.py`**

```python
import os
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich import box
from src.comparison import AbilityDelta

console = Console()


def print_dungeon_table(
    deltas: list[AbilityDelta],
    dungeon_name: str,
    bracket: int,
    your_dps: float,
    top_n_dps: float,
    top_n: int,
) -> None:
    dps_gap = ((your_dps - top_n_dps) / top_n_dps * 100) if top_n_dps else 0.0
    gap_color = "green" if dps_gap >= 0 else "red"
    console.print(f"\n[bold]Dungeon Breakdown — {dungeon_name} +{bracket}[/bold]")
    console.print(
        f"Your DPS: [cyan]{your_dps:,.0f}[/cyan]  "
        f"Top {top_n} avg: [orange1]{top_n_dps:,.0f}[/orange1]  "
        f"Gap: [{gap_color}]{dps_gap:+.1f}%[/{gap_color}]\n"
    )
    table = Table(box=box.SIMPLE, show_header=True, header_style="dim")
    table.add_column("Ability", style="white")
    table.add_column("Your Casts", justify="right")
    table.add_column(f"Top {top_n} Avg", justify="right")
    table.add_column("Cast Δ", justify="right")
    table.add_column("Your GCD%", justify="right")
    table.add_column(f"Top {top_n} GCD%", justify="right")
    table.add_column("GCD Δ", justify="right")
    for d in deltas:
        color = "green" if d.gcd_delta > 0 else ("red" if d.gcd_delta < 0 else "dim")
        table.add_row(
            d.ability_name,
            str(d.your_casts),
            f"{d.top_n_avg:.1f}",
            f"{d.cast_delta:+.1f}",
            f"{d.your_gcd_pct:.1f}%",
            f"{d.top_n_gcd_pct:.1f}%",
            f"[{color}]{d.gcd_delta:+.1f}%[/{color}]",
        )
    console.print(table)


def print_overview_results(results: list[dict]) -> None:
    console.print("\n[bold]Season Overview[/bold]\n")
    for r in results:
        console.print(
            f"[bold]{r['dungeon']} +{r['bracket']}[/bold]  "
            f"Clear time: {r['fight_duration_s']}s  "
            f"Top {r['top_n']} avg DPS: [orange1]{r['top_n_dps']:,.0f}[/orange1]"
        )
    console.print()


def print_compare_table(
    your_casts: dict[int, int],
    their_casts: dict[int, int],
    ability_names: dict[int, str],
    your_name: str,
    their_name: str,
) -> None:
    all_ids = sorted(
        set(your_casts) | set(their_casts),
        key=lambda i: your_casts.get(i, 0) + their_casts.get(i, 0),
        reverse=True,
    )
    console.print(f"\n[bold]1v1 — {your_name} vs {their_name}[/bold]\n")
    table = Table(box=box.SIMPLE, show_header=True, header_style="dim")
    table.add_column("Ability", style="white")
    table.add_column(your_name[:16], justify="right")
    table.add_column(their_name[:16], justify="right")
    table.add_column("Δ", justify="right")
    for aid in all_ids:
        yours = your_casts.get(aid, 0)
        theirs = their_casts.get(aid, 0)
        diff = yours - theirs
        color = "green" if diff > 0 else ("red" if diff < 0 else "dim")
        table.add_row(
            ability_names.get(aid, str(aid)),
            str(yours),
            str(theirs),
            f"[{color}]{diff:+d}[/{color}]",
        )
    console.print(table)
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/test_report.py -v
```

Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add src/report.py tests/test_report.py
git commit -m "feat(report): add rich terminal tables for all three tiers"
```

---

### Task 10: `src/report.py` — HTML report generation

**Files:**
- Modify: `src/report.py`
- Modify: `tests/test_report.py`

- [ ] **Step 1: Add HTML tests to `tests/test_report.py`**

Append to the existing file:

```python
# append to tests/test_report.py
import tempfile
from src.report import save_html_report, build_dungeon_html, build_overview_html, build_compare_html


def test_save_html_report_creates_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = save_html_report("<p>test</p>", output_dir=tmpdir)
    assert path.endswith(".html")
    assert os.path.exists(path)


def test_build_dungeon_html_contains_ability_names():
    html = build_dungeon_html(_DELTAS, "Maisara Caverns", 18, 245312.0, 271044.0, 10, "Bêngi")
    assert "Arcane Blast" in html
    assert "Arcane Pulse" in html
    assert "Maisara Caverns" in html


def test_build_overview_html_contains_dungeons():
    results = [{"dungeon": "Maisara Caverns", "bracket": 18, "top_n_dps": 271044.0, "top_n": 10, "fight_duration_s": 134}]
    html = build_overview_html(results, "Bêngi", 18, 10)
    assert "Maisara Caverns" in html
    assert "Bêngi" in html


def test_build_compare_html_contains_both_names():
    html = build_compare_html(
        {30451: 142}, {30451: 126},
        {30451: "Arcane Blast"},
        "Bêngi", "Playerone",
        "Maisara Caverns", 18,
    )
    assert "Bêngi" in html
    assert "Playerone" in html
    assert "Arcane Blast" in html


def test_html_report_is_utf8():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = save_html_report("<p>Bêngi</p>", output_dir=tmpdir)
    content = open(path, encoding="utf-8").read()
    assert "Bêngi" in content
```

- [ ] **Step 2: Run new tests — verify they fail**

```bash
pytest tests/test_report.py -v -k "html"
```

Expected: `ImportError` (functions not yet defined)

- [ ] **Step 3: Add HTML functions to `src/report.py`**

Append to the existing `src/report.py`:

```python
_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #0d0d0f; color: #ccc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 13px; padding: 24px 28px; }
h1 { color: #fff; font-size: 18px; margin-bottom: 4px; }
h2 { color: #fff; font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em; margin: 20px 0 10px; }
.meta { color: #666; font-size: 12px; margin-bottom: 20px; }
.cards { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 20px; }
.card { background: #141418; border: 1px solid #222; border-radius: 6px; padding: 12px 16px; min-width: 160px; }
.card .label { font-size: 10px; color: #555; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 4px; }
.card .value { font-size: 18px; font-weight: 700; }
table { width: 100%; border-collapse: collapse; margin-bottom: 24px; }
th { text-align: left; color: #555; font-size: 10px; text-transform: uppercase; letter-spacing: 0.06em; padding: 6px 10px; border-bottom: 1px solid #1e1e1e; }
td { padding: 7px 10px; border-bottom: 1px solid #181818; }
.pos { color: #2ecc71; font-weight: 600; }
.neg { color: #e74c3c; font-weight: 600; }
.neu { color: #555; }
.split { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.player-col { background: #141418; border: 1px solid #222; border-radius: 6px; padding: 14px; }
.player-col h3 { color: #fff; margin-bottom: 10px; font-size: 13px; }
"""

_HTML_FRAME = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>wow-wl-analyzer</title>
<style>{css}</style>
</head>
<body>{body}</body>
</html>
"""


def save_html_report(body: str, output_dir: str = "output") -> str:
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    path = os.path.join(output_dir, f"report_{ts}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(_HTML_FRAME.format(css=_CSS, body=body))
    return path


def build_dungeon_html(
    deltas: list[AbilityDelta],
    dungeon_name: str,
    bracket: int,
    your_dps: float,
    top_n_dps: float,
    top_n: int,
    your_name: str,
) -> str:
    dps_gap = ((your_dps - top_n_dps) / top_n_dps * 100) if top_n_dps else 0.0
    gap_cls = "pos" if dps_gap >= 0 else "neg"
    rows = "".join(
        f"<tr>"
        f"<td>{d.ability_name}</td>"
        f"<td>{d.your_casts}</td>"
        f"<td>{d.top_n_avg:.1f}</td>"
        f"<td class=\"{'pos' if d.cast_delta > 0 else ('neg' if d.cast_delta < 0 else 'neu')}\">{d.cast_delta:+.1f}</td>"
        f"<td>{d.your_gcd_pct:.1f}%</td>"
        f"<td>{d.top_n_gcd_pct:.1f}%</td>"
        f"<td class=\"{'pos' if d.gcd_delta > 0 else ('neg' if d.gcd_delta < 0 else 'neu')}\">{d.gcd_delta:+.1f}%</td>"
        f"</tr>"
        for d in deltas
    )
    return (
        f"<h1>{your_name} — {dungeon_name} +{bracket}</h1>"
        f"<p class=\"meta\">Your DPS: {your_dps:,.0f} &nbsp;|&nbsp; "
        f"Top {top_n} avg: {top_n_dps:,.0f} &nbsp;|&nbsp; "
        f"Gap: <span class=\"{gap_cls}\">{dps_gap:+.1f}%</span></p>"
        f"<h2>Ability Breakdown</h2>"
        f"<table><thead><tr>"
        f"<th>Ability</th><th>Your Casts</th><th>Top {top_n} Avg</th>"
        f"<th>Cast Δ</th><th>Your GCD%</th><th>Top {top_n} GCD%</th><th>GCD Δ</th>"
        f"</tr></thead><tbody>{rows}</tbody></table>"
    )


def build_overview_html(
    results: list[dict],
    your_name: str,
    bracket: int,
    top_n: int,
) -> str:
    cards = "".join(
        f"<div class=\"card\">"
        f"<div class=\"label\">{r['dungeon']}</div>"
        f"<div class=\"value\">+{r['bracket']} &nbsp; {r['fight_duration_s']}s</div>"
        f"<div class=\"meta\">Top {r['top_n']} avg: {r['top_n_dps']:,.0f} dps</div>"
        f"</div>"
        for r in results
    )
    return (
        f"<h1>{your_name} — Season Overview</h1>"
        f"<p class=\"meta\">Bracket +{bracket} &nbsp;|&nbsp; Comparing vs Top {top_n}</p>"
        f"<h2>Dungeons Run</h2>"
        f"<div class=\"cards\">{cards}</div>"
    )


def build_compare_html(
    your_casts: dict[int, int],
    their_casts: dict[int, int],
    ability_names: dict[int, str],
    your_name: str,
    their_name: str,
    dungeon_name: str,
    bracket: int,
) -> str:
    all_ids = sorted(
        set(your_casts) | set(their_casts),
        key=lambda i: your_casts.get(i, 0) + their_casts.get(i, 0),
        reverse=True,
    )

    def _rows(casts: dict[int, int], other: dict[int, int], is_you: bool) -> str:
        out = ""
        for aid in all_ids:
            mine = casts.get(aid, 0)
            theirs = other.get(aid, 0)
            diff = mine - theirs
            cls = "pos" if diff > 0 else ("neg" if diff < 0 else "neu")
            out += (
                f"<div style=\"display:flex;justify-content:space-between;padding:5px 0;"
                f"border-bottom:1px solid #1c1c1c\">"
                f"<span>{ability_names.get(aid, str(aid))}</span>"
                f"<span class=\"{cls if is_you else 'neu'}\">{mine}</span>"
                f"</div>"
            )
        return out

    return (
        f"<h1>1v1 — {your_name} vs {their_name}</h1>"
        f"<p class=\"meta\">{dungeon_name} +{bracket}</p>"
        f"<div class=\"split\">"
        f"<div class=\"player-col\"><h3>{your_name}</h3>{_rows(your_casts, their_casts, True)}</div>"
        f"<div class=\"player-col\"><h3>{their_name}</h3>{_rows(their_casts, your_casts, False)}</div>"
        f"</div>"
    )
```

- [ ] **Step 4: Run all report tests**

```bash
pytest tests/test_report.py -v
```

Expected: `8 passed`

- [ ] **Step 5: Commit**

```bash
git add src/report.py tests/test_report.py
git commit -m "feat(report): add HTML report generation for all three tiers"
```

---

### Task 11: `analyze.py` skeleton + `setup` command

**Files:**
- Create: `analyze.py`
- Create: `tests/test_setup.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_setup.py
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import StringIO


def _run_setup(inputs: list[str], mock_char: dict, tmp_path: Path):
    input_iter = iter(inputs)
    env_path = tmp_path / ".env"

    with patch("builtins.input", side_effect=lambda _="": next(input_iter)), \
         patch("getpass.getpass", return_value="secret123"), \
         patch("src.auth.get_access_token", return_value="tok"), \
         patch("src.character.lookup_character", return_value=mock_char), \
         patch("src.character.get_specs_for_class", return_value=["Arcane", "Fire", "Frost"]), \
         patch("src.report.console"), \
         patch("builtins.open", unittest_open := MagicMock()), \
         patch("pathlib.Path.write_text") as mock_write:
        import analyze
        from analyze import cmd_setup
        args = MagicMock()
        cmd_setup(args, env_path=str(env_path))
        return mock_write


def test_setup_writes_env_file(tmp_path):
    mock_char = {"name": "Bêngi", "class_id": 4, "class_name": "Mage"}
    inputs = ["client-id", "Bêngi", "Illidan", "US", "1", "10", "18"]
    with patch("builtins.input", side_effect=iter(inputs)), \
         patch("getpass.getpass", return_value="secret123"), \
         patch("src.auth.get_access_token", return_value="tok"), \
         patch("src.character.lookup_character", return_value=mock_char), \
         patch("src.character.get_specs_for_class", return_value=["Arcane", "Fire", "Frost"]), \
         patch("src.report.console"), \
         patch("pathlib.Path.write_text") as mock_write:
        import importlib, analyze
        importlib.reload(analyze)
        from analyze import cmd_setup
        cmd_setup(MagicMock(), env_path=str(tmp_path / ".env"))
    mock_write.assert_called_once()
    written = mock_write.call_args[0][0]
    assert "Bêngi" in written
    assert "Mage" in written
    assert "Arcane" in written
    assert "encoding" in str(mock_write.call_args)


def test_setup_invalid_credentials_exits(tmp_path):
    with patch("builtins.input", side_effect=iter(["bad-id"])), \
         patch("getpass.getpass", return_value="bad-secret"), \
         patch("src.auth.get_access_token", side_effect=ValueError("Invalid WCL credentials")), \
         patch("src.report.console"), \
         pytest.raises(SystemExit):
        import analyze
        from analyze import cmd_setup
        cmd_setup(MagicMock(), env_path=str(tmp_path / ".env"))
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_setup.py -v
```

Expected: `ModuleNotFoundError: No module named 'analyze'`

- [ ] **Step 3: Implement `analyze.py` with skeleton and `cmd_setup`**

```python
#!/usr/bin/env python3
"""wow-wl-analyzer — WoW Mythic+ cast comparison tool."""
import argparse
import getpass
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(encoding="utf-8")


def _require_env(key: str) -> str:
    val = os.getenv(key)
    if not val:
        print(f"Missing {key}. Run: python analyze.py setup", file=sys.stderr)
        sys.exit(1)
    return val


def cmd_setup(args, env_path: str = ".env") -> None:
    from src.auth import get_access_token
    from src.character import lookup_character, get_specs_for_class
    from src.report import console

    console.print("\n[bold]wow-wl-analyzer setup[/bold]")
    console.print("─" * 52)
    console.print("\nCreate a WCL API client at:")
    console.print("  https://www.warcraftlogs.com/api/clients/\n")

    client_id = input("WCL Client ID: ").strip()
    client_secret = getpass.getpass("WCL Client Secret: ").strip()

    try:
        token = get_access_token(client_id, client_secret)
        console.print("[green]✓ Credentials validated[/green]")
    except ValueError as e:
        console.print(f"[red]✗ {e}[/red]")
        sys.exit(1)

    print()
    char_name = input("Character name: ").strip()
    realm = input("Realm: ").strip()
    region = (input("Region [US]: ").strip() or "US").upper()

    try:
        char = lookup_character(token, char_name, realm, region)
        console.print(f"[green]✓ Found: {char['name']}-{realm} ({char['class_name']})[/green]")
    except ValueError as e:
        console.print(f"[red]✗ {e}[/red]")
        sys.exit(1)

    specs = get_specs_for_class(char["class_name"])
    spec_menu = ", ".join(f"[{i + 1}] {s}" for i, s in enumerate(specs))
    console.print(f"Specs: {spec_menu}")
    spec_input = (input("Which spec? [1]: ").strip() or "1")
    try:
        spec_name = specs[int(spec_input) - 1]
    except (ValueError, IndexError):
        console.print("[red]Invalid spec choice[/red]")
        sys.exit(1)

    print()
    top_n = int(input("Top N parses [10]: ").strip() or "10")
    bracket = int(input("Default keystone bracket [18]: ").strip() or "18")

    content = (
        "# WCL API credentials\n"
        f"WCL_CLIENT_ID={client_id}\n"
        f"WCL_CLIENT_SECRET={client_secret}\n\n"
        "# Your character\n"
        f"CHARACTER_NAME={char_name}\n"
        f"CHARACTER_REALM={realm}\n"
        f"CHARACTER_REGION={region}\n"
        f"CHARACTER_CLASS={char['class_name']}\n"
        f"CHARACTER_SPEC={spec_name}\n\n"
        "# Analysis defaults\n"
        f"TOP_N_PARSES={top_n}\n"
        f"DEFAULT_BRACKET={bracket}\n"
    )
    Path(env_path).write_text(content, encoding="utf-8")
    console.print(f"\n[green]✓ Config saved to {env_path}[/green]")
    console.print("\nYou're set. Try:")
    console.print(f"  python analyze.py overview --report <code>")
    console.print(f"  python analyze.py dungeon --report <code> --dungeon \"Maisara Caverns\" --bracket {bracket}")
    console.print(f"  python analyze.py compare --report <code> --fight <id> --vs <report> --vs-fight <id>")


def cmd_overview(args) -> None:
    pass  # Task 12


def cmd_dungeon(args) -> None:
    pass  # Task 13


def cmd_compare(args) -> None:
    pass  # Task 14


def main() -> None:
    parser = argparse.ArgumentParser(prog="analyze.py", description="WoW M+ cast analyzer")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("setup", help="Configure credentials and character")

    p_ov = sub.add_parser("overview", help="Season overview across all dungeons")
    p_ov.add_argument("--report", required=True)
    p_ov.add_argument("--top", type=int, default=None)
    p_ov.add_argument("--bracket", type=int, default=None)

    p_dn = sub.add_parser("dungeon", help="Ability-level breakdown for one dungeon")
    p_dn.add_argument("--report", required=True)
    p_dn.add_argument("--dungeon", required=True)
    p_dn.add_argument("--bracket", type=int, default=None)
    p_dn.add_argument("--top", type=int, default=None)

    p_cp = sub.add_parser("compare", help="1v1 cast-by-cast comparison")
    p_cp.add_argument("--report", required=True)
    p_cp.add_argument("--fight", type=int, required=True)
    p_cp.add_argument("--vs", required=True)
    p_cp.add_argument("--vs-fight", type=int, required=True)

    args = parser.parse_args()
    {"setup": cmd_setup, "overview": cmd_overview, "dungeon": cmd_dungeon, "compare": cmd_compare}[args.command](args)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run setup tests**

```bash
pytest tests/test_setup.py -v
```

Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add analyze.py tests/test_setup.py
git commit -m "feat(cli): add analyze.py skeleton and setup command"
```

---

### Task 12: `analyze.py` — `overview` command

**Files:**
- Modify: `analyze.py`
- Create: `tests/test_overview.py`

- [ ] **Step 1: Write failing tests**

```python
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
         patch("src.client.query", side_effect=[_report_fights(), rankings_resp]), \
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
    # fight is +19, but bracket is 18 — should be excluded
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
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_overview.py -v
```

Expected: `AssertionError` (cmd_overview is a stub)

- [ ] **Step 3: Implement `cmd_overview` in `analyze.py`**

Replace the `def cmd_overview(args) -> None: pass` stub:

```python
def cmd_overview(args) -> None:
    from src.auth import get_access_token
    from src.client import query as wcl_query
    from src.constants import DUNGEONS
    from src.queries import GET_REPORT_FIGHTS
    from src.rankings import fetch_top_rankings
    from src import report as rpt

    client_id = _require_env("WCL_CLIENT_ID")
    client_secret = _require_env("WCL_CLIENT_SECRET")
    class_name = _require_env("CHARACTER_CLASS")
    spec_name = _require_env("CHARACTER_SPEC")
    region = os.getenv("CHARACTER_REGION", "US")
    top_n = args.top or int(os.getenv("TOP_N_PARSES", "10"))
    bracket = args.bracket or int(os.getenv("DEFAULT_BRACKET", "18"))

    token = get_access_token(client_id, client_secret)
    data = wcl_query(token, GET_REPORT_FIGHTS, {"code": args.report})
    fights = data["reportData"]["report"]["fights"]

    results = []
    for dungeon_name, encounter_id in DUNGEONS.items():
        matching = [
            f for f in fights
            if f["encounterID"] == encounter_id
            and f.get("keystoneLevel") == bracket
            and f.get("kill")
        ]
        if not matching:
            continue
        best = min(matching, key=lambda f: f["endTime"] - f["startTime"])
        duration_s = round((best["endTime"] - best["startTime"]) / 1000)

        rankings = fetch_top_rankings(token, encounter_id, class_name, spec_name, region, bracket, top_n)
        if not rankings:
            continue
        top_n_dps = sum(r["amount"] for r in rankings) / len(rankings)

        results.append({
            "dungeon": dungeon_name,
            "bracket": bracket,
            "fight_id": best["id"],
            "fight_duration_s": duration_s,
            "top_n_dps": top_n_dps,
            "top_n": top_n,
            "rankings": rankings,
        })

    rpt.print_overview_results(results)
    body = rpt.build_overview_html(results, os.getenv("CHARACTER_NAME", ""), bracket, top_n)
    path = rpt.save_html_report(body)
    rpt.console.print(f"\n[dim]Full report → {path}[/dim]")
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_overview.py -v
```

Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add analyze.py tests/test_overview.py
git commit -m "feat(cli): add overview command — per-dungeon top-N DPS comparison"
```

---

### Task 13: `analyze.py` — `dungeon` command

**Files:**
- Modify: `analyze.py`
- Create: `tests/test_dungeon.py`

- [ ] **Step 1: Write failing tests**

```python
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

    side_effects = [
        _fights_resp(),
        _rankings_resp(),
        _cast_events_resp(player_casts),
        _master_resp(),
        _cast_events_resp(comp_casts),
    ]

    with patch.dict("os.environ", _ENV), \
         patch("src.auth.get_access_token", return_value="tok"), \
         patch("src.client.query", side_effect=side_effects), \
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
    wrong_bracket = _fights_resp(keystone=20)  # looking for 18
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
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_dungeon.py -v
```

Expected: failures (stub)

- [ ] **Step 3: Implement `cmd_dungeon` in `analyze.py`**

Replace the `def cmd_dungeon(args) -> None: pass` stub:

```python
def cmd_dungeon(args) -> None:
    from src.auth import get_access_token
    from src.client import query as wcl_query
    from src.constants import DUNGEONS
    from src.queries import GET_REPORT_FIGHTS
    from src.rankings import fetch_top_rankings
    from src.events import fetch_cast_counts, find_actor_id, extract_ability_names
    from src.comparison import compute_comparison
    from src import report as rpt

    client_id = _require_env("WCL_CLIENT_ID")
    client_secret = _require_env("WCL_CLIENT_SECRET")
    char_name = _require_env("CHARACTER_NAME")
    class_name = _require_env("CHARACTER_CLASS")
    spec_name = _require_env("CHARACTER_SPEC")
    region = os.getenv("CHARACTER_REGION", "US")
    top_n = args.top or int(os.getenv("TOP_N_PARSES", "10"))
    bracket = args.bracket or int(os.getenv("DEFAULT_BRACKET", "18"))

    encounter_id = DUNGEONS.get(args.dungeon)
    if encounter_id is None:
        valid = ", ".join(f'"{d}"' for d in DUNGEONS)
        rpt.console.print(f"[red]Unknown dungeon '{args.dungeon}'. Valid: {valid}[/red]")
        sys.exit(1)

    token = get_access_token(client_id, client_secret)
    data = wcl_query(token, GET_REPORT_FIGHTS, {"code": args.report})
    report_data = data["reportData"]["report"]
    fights = report_data["fights"]
    master = report_data["masterData"]
    ability_names = extract_ability_names(master)

    matching = [
        f for f in fights
        if f["encounterID"] == encounter_id
        and f.get("keystoneLevel") == bracket
        and f.get("kill")
    ]
    if not matching:
        rpt.console.print(
            f"[red]No +{bracket} kill found for '{args.dungeon}' in report '{args.report}'.[/red]"
        )
        sys.exit(1)

    best = min(matching, key=lambda f: f["endTime"] - f["startTime"])
    player_actor_id = next(
        (a["id"] for a in master["actors"] if a["name"].lower() == char_name.lower()), None
    )
    if player_actor_id is None:
        rpt.console.print(f"[red]Could not find actor for '{char_name}' in report.[/red]")
        sys.exit(1)

    rpt.console.print(f"Fetching your casts for {args.dungeon} +{bracket}...")
    player_casts = fetch_cast_counts(
        token, args.report, best["id"], player_actor_id,
        float(best["startTime"]), float(best["endTime"])
    )

    rpt.console.print(f"Fetching top {top_n} {class_name} {spec_name} rankings...")
    rankings = fetch_top_rankings(token, encounter_id, class_name, spec_name, region, bracket, top_n)
    if not rankings:
        rpt.console.print(f"[yellow]No rankings found for {class_name}/{spec_name} at +{bracket}.[/yellow]")
        sys.exit(0)

    top_n_dps = sum(r["amount"] for r in rankings) / len(rankings)
    competitor_casts: list[dict[int, int]] = []
    for rank in rankings:
        comp_actor_id = find_actor_id(token, rank["report_code"], rank["name"])
        casts = fetch_cast_counts(
            token, rank["report_code"], rank["fight_id"], comp_actor_id,
            float(report_data["startTime"]), float(report_data["endTime"])
        )
        competitor_casts.append(casts)

    deltas = compute_comparison(player_casts, competitor_casts, ability_names)
    duration_s = round((best["endTime"] - best["startTime"]) / 1000)
    player_dps = sum(player_casts.values()) / duration_s if duration_s else 0

    rpt.print_dungeon_table(deltas, args.dungeon, bracket, player_dps, top_n_dps, top_n)
    body = rpt.build_dungeon_html(deltas, args.dungeon, bracket, player_dps, top_n_dps, top_n, char_name)
    path = rpt.save_html_report(body)
    rpt.console.print(f"\n[dim]Full report → {path}[/dim]")
```

> **Note:** `player_dps` here is cast-events-per-second, not actual damage. For the dungeon command this is fine as a relative measure; the terminal and HTML already show the top-N avg DPS from the WCL leaderboard for context. Actual damage per cast is a future enhancement.

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_dungeon.py -v
```

Expected: `2 passed`

- [ ] **Step 5: Run the full test suite**

```bash
pytest -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add analyze.py tests/test_dungeon.py
git commit -m "feat(cli): add dungeon command with keystone-matched cast comparison"
```

---

### Task 14: `analyze.py` — `compare` command

**Files:**
- Modify: `analyze.py`
- Create: `tests/test_compare.py`

- [ ] **Step 1: Write failing tests**

```python
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
         patch("src.client.query", side_effect=side_effects), \
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
```

- [ ] **Step 2: Run test — verify it fails**

```bash
pytest tests/test_compare.py -v
```

Expected: failure (stub)

- [ ] **Step 3: Implement `cmd_compare` in `analyze.py`**

Replace the `def cmd_compare(args) -> None: pass` stub:

```python
def cmd_compare(args) -> None:
    from src.auth import get_access_token
    from src.events import fetch_cast_counts, find_actor_id, extract_ability_names
    from src.queries import GET_REPORT_MASTER_DATA
    from src.client import query as wcl_query
    from src import report as rpt

    client_id = _require_env("WCL_CLIENT_ID")
    client_secret = _require_env("WCL_CLIENT_SECRET")
    char_name = _require_env("CHARACTER_NAME")

    token = get_access_token(client_id, client_secret)

    rpt.console.print(f"Fetching your report masterData...")
    my_master_data = wcl_query(token, GET_REPORT_MASTER_DATA, {"code": args.report})
    my_master = my_master_data["reportData"]["report"]["masterData"]
    ability_names = extract_ability_names(my_master)
    my_actor_id = next(
        (a["id"] for a in my_master["actors"] if a["name"].lower() == char_name.lower()),
        None
    )
    if my_actor_id is None:
        rpt.console.print(f"[red]Could not find '{char_name}' in report '{args.report}'.[/red]")
        sys.exit(1)

    rpt.console.print(f"Fetching your casts (fight {args.fight})...")
    my_casts = fetch_cast_counts(token, args.report, args.fight, my_actor_id, 0.0, 99999999.0)

    rpt.console.print(f"Fetching competitor masterData...")
    their_master_data = wcl_query(token, GET_REPORT_MASTER_DATA, {"code": args.vs})
    their_master = their_master_data["reportData"]["report"]["masterData"]
    their_actor = their_master["actors"][0] if their_master["actors"] else None
    if their_actor is None:
        rpt.console.print(f"[red]No players found in report '{args.vs}'.[/red]")
        sys.exit(1)
    their_name = their_actor["name"]
    their_actor_id = their_actor["id"]

    rpt.console.print(f"Fetching {their_name}'s casts (fight {args.vs_fight})...")
    their_casts = fetch_cast_counts(token, args.vs, args.vs_fight, their_actor_id, 0.0, 99999999.0)

    rpt.print_compare_table(my_casts, their_casts, ability_names, char_name, their_name)
    body = rpt.build_compare_html(
        my_casts, their_casts, ability_names,
        char_name, their_name, "Mythic+", 0
    )
    path = rpt.save_html_report(body)
    rpt.console.print(f"\n[dim]Full report → {path}[/dim]")
```

- [ ] **Step 4: Run all tests**

```bash
pytest -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add analyze.py tests/test_compare.py
git commit -m "feat(cli): add compare command for 1v1 cast-by-cast comparison"
```

---

### Task 15: README + push

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write `README.md`**

```markdown
# wow-wl-analyzer

Compare your World of Warcraft Mythic+ cast usage against top-ranked players using the [Warcraft Logs](https://www.warcraftlogs.com) API.

**Three analysis tiers:**
- `overview` — which dungeons you ran, and how the top-N averages compare
- `dungeon` — ability-by-ability cast breakdown vs top-N for a specific dungeon + keystone level
- `compare` — side-by-side cast counts vs one specific player's run

## Prerequisites

- Python 3.10 or higher
- A Warcraft Logs API client — create one at [warcraftlogs.com/api/clients](https://www.warcraftlogs.com/api/clients/)

## Setup

```bash
git clone https://github.com/BenGiese22/wow-wl-analyzer.git
cd wow-wl-analyzer
pip install -r requirements.txt
python analyze.py setup
```

`setup` will prompt for your API credentials and character, validate them, and save everything to `.env`.

## Usage

### Season overview
```bash
python analyze.py overview --report <your-report-code>
# Optional: --top 10 --bracket 18
```

### Dungeon breakdown
```bash
python analyze.py dungeon --report <code> --dungeon "Maisara Caverns" --bracket 18
# Optional: --top 10
```

### 1v1 comparison
```bash
python analyze.py compare --report <your-code> --fight <your-fight-id> \
  --vs <their-report-code> --vs-fight <their-fight-id>
```

Report codes come from WCL report URLs, e.g. `warcraftlogs.com/reports/aAbBcCdDeE` → code is `aAbBcCdDeE`.

Fight IDs are printed in the `overview` and `dungeon` outputs, or visible in WCL's fight selector.

## Output

Each command prints a summary to the terminal and saves a full HTML report to `output/`.

## Midnight Season 1 Dungeons

| Dungeon | Type |
|---------|------|
| Algeth'ar Academy | Legacy (Dragonflight) |
| Magisters' Terrace | New (Midnight) |
| Maisara Caverns | New (Midnight) |
| Nexus-Point Xenas | New (Midnight) |
| Pit of Saron | Legacy (Wrath) |
| Seat of the Triumvirate | Legacy (Legion) |
| Skyreach | Legacy (Warlords) |
| Windrunner Spire | New (Midnight) |
```

- [ ] **Step 2: Run the full suite one final time**

```bash
pytest -v
```

Expected: all tests pass, no warnings about missing modules.

- [ ] **Step 3: Commit and push**

```bash
git add README.md
git commit -m "docs(readme): add setup and usage guide"
git push origin main
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task(s) |
|-----------------|---------|
| OAuth2 client credentials | Task 2 |
| GraphQL wrapper | Task 3 |
| Dungeon → encounter ID map | Task 4 |
| Character lookup + class/spec | Task 5 |
| Top-N rankings fetch | Task 6 |
| Paginated cast events | Task 7 |
| GCD% delta calculation | Task 8 |
| Terminal output (rich) | Task 9 |
| HTML report (all tiers) | Task 10 |
| setup command + .env write | Task 11 |
| overview command | Task 12 |
| dungeon command + keystone matching | Task 13 |
| compare command | Task 14 |
| README / sharability | Task 15 |
| UTF-8 character names | Tasks 5, 11 (write_text encoding param) |
| Paginated events never truncated | Task 7 (loops until nextPageTimestamp is null) |
| Empty rankings error handling | Tasks 12, 13 |
| No credentials in source | .gitignore + .env.example |

No gaps found.
