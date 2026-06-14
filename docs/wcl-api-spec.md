# Warcraft Logs GraphQL API v2 — Spec

> Derived from live API introspection against `https://www.warcraftlogs.com/api/v2/client`
> on 2026-06-14. All type names, field names, and IDs are verified against the live schema.

## Authentication

WCL uses OAuth 2.0 **client credentials** flow. No user interaction required.

```bash
curl -X POST https://www.warcraftlogs.com/oauth/token \
  -u "$WCL_CLIENT_ID:$WCL_CLIENT_SECRET" \
  -d "grant_type=client_credentials"
```

Response:
```json
{ "access_token": "eyJ...", "token_type": "Bearer", "expires_in": 3600 }
```

Include the token on every GraphQL request:
```
Authorization: Bearer <access_token>
```

**Endpoint**: `POST https://www.warcraftlogs.com/api/v2/client`
**Content-Type**: `application/json`
**Body**: `{ "query": "<graphql query string>" }`

Tokens expire in 1 hour. Re-request before making calls or when a 401 is returned.

---

## Top-Level Query Fields

| Field | Description |
|-------|-------------|
| `characterData` | Retrieve individual characters or filtered collections |
| `gameData` | Static game data: abilities, classes, items, NPCs |
| `guildData` | Individual guilds or filtered collections |
| `rateLimitData` | Points spent by this API key (use to avoid rate limits) |
| `reportData` | Individual reports or collections by guild/user |
| `userData` | Authorized user's ID and username |
| `worldData` | Expansions, regions, zones, encounters |

---

## worldData — Expansions, Zones, Encounters

### Get all expansions
```graphql
{
  worldData {
    expansions {
      id
      name
    }
  }
}
```

**Midnight expansion ID: 7**

### Get zones and encounters for an expansion
```graphql
{
  worldData {
    expansion(id: 7) {
      zones {
        id
        name
        encounters {
          id
          name
        }
      }
    }
  }
}
```

### Midnight Season 1 M+ — Verified Zone & Encounter IDs

**Zone**: `Mythic+ Season 1` — **id: 47**

| Dungeon | Encounter ID | Type |
|---------|-------------|------|
| Algeth'ar Academy | 112526 | Legacy (Dragonflight) |
| Magisters' Terrace | 12811 | New (Midnight) |
| Maisara Caverns | 12874 | New (Midnight) |
| Nexus-Point Xenas | 12915 | New (Midnight) |
| Pit of Saron | 10658 | Legacy (Wrath) |
| Seat of the Triumvirate | 361753 | Legacy (Legion) |
| Skyreach | 61209 | Legacy (Warlords) |
| Windrunner Spire | 12805 | New (Midnight) |

---

## worldData — Character Rankings (Top Parses)

Used to find the top-N players of a given class/spec on a specific dungeon.

```graphql
{
  worldData {
    encounter(id: <ENCOUNTER_ID>) {
      characterRankings(
        className: "Mage"
        specName: "Arcane"
        serverRegion: "US"
        difficulty: 10
        page: 1
        metric: dps
        includeOtherPlayers: false
        includeCombatantInfo: false
      )
    }
  }
}
```

### characterRankings Arguments

| Arg | Type | Description |
|-----|------|-------------|
| `className` | String | Class name as a string (e.g., `"Mage"`) |
| `specName` | String | Spec name as a string (e.g., `"Arcane"`) |
| `serverRegion` | String | Region filter (e.g., `"US"`, `"EU"`, `"KR"`) |
| `serverSlug` | String | Optional: narrow to a specific realm |
| `difficulty` | Int | Keystone level or raid difficulty; for M+ use `10` (Mythic+) |
| `page` | Int | Pagination page (1-indexed) |
| `metric` | CharacterRankingMetricType | `dps`, `hps`, `krsi`, etc. |
| `bracket` | Int | Keystone level bracket (e.g., `18` for +18) |
| `partition` | Int | Season partition (omit for current) |
| `leaderboard` | LeaderboardRank | Filter to leaderboard-eligible runs |
| `includeCombatantInfo` | Boolean | Include combatant info in response |
| `includeOtherPlayers` | Boolean | Include other players in the group |
| `filter` | String | Expression filter |

> **Note**: `characterRankings` returns a JSON scalar, not a typed object. The response is
> a JSON blob inside the GraphQL response. Parse it with `json.loads()`.

### Example Response Shape (characterRankings)
```json
{
  "rankings": [
    {
      "name": "Playerone",
      "class": "Mage",
      "spec": "Arcane",
      "amount": 245312.4,
      "hardModeLevel": 20,
      "duration": 2134567,
      "startTime": 1749123456789,
      "report": {
        "code": "aAbBcCdDeE",
        "fightID": 3,
        "startTime": 1749123456000
      },
      "server": { "name": "Illidan", "region": "US" }
    }
  ],
  "page": 1,
  "hasMorePages": false,
  "count": 10,
  "total": 10
}
```

---

## reportData — Fetch a Specific Report

```graphql
{
  reportData {
    report(code: "aAbBcCdDeE") {
      code
      title
      startTime
      endTime
      region { name }
      fights(killType: Kills) {
        id
        encounterID
        name
        startTime
        endTime
        keystoneLevel
        keystoneAffixes
        keystoneTime
        averageItemLevel
      }
      masterData(translate: true) {
        actors(type: "Player") {
          id
          name
          server
          subType
          gameID
        }
      }
    }
  }
}
```

### Report Fields

| Field | Description |
|-------|-------------|
| `code` | Unique report identifier |
| `title` | Report title |
| `startTime` / `endTime` | UNIX ms timestamps |
| `fights` | List of encounters in this report |
| `masterData` | Player list, ability list, NPC list |
| `events` | Paginated combat events (casts, damage, deaths) |
| `table` | Aggregated data table (damage done, healing, etc.) |
| `rankings` | Rankings info for fights in this report |
| `playerDetails` | Per-player spec, talents, gear summary |

### fights Arguments

| Arg | Type | Description |
|-----|------|-------------|
| `killType` | KillType | `Kills`, `Wipes`, `All`, `Encounters` |
| `fightIDs` | [Int] | Filter to specific fight IDs |
| `encounterID` | Int | Filter to a specific encounter |
| `difficulty` | Int | Difficulty filter |

### ReportFight Fields (M+ relevant)

| Field | Description |
|-------|-------------|
| `id` | Fight ID within report |
| `encounterID` | Maps to worldData encounter IDs above |
| `keystoneLevel` | Keystone level for this run |
| `keystoneAffixes` | Array of affix IDs active |
| `keystoneTime` | Time limit in ms |
| `startTime` / `endTime` | Relative to report startTime (ms) |
| `averageItemLevel` | Average ilvl of the group |

---

## reportData — Events (Cast-Level Data)

The most granular data available: every individual event in the combat log.

```graphql
{
  reportData {
    report(code: "aAbBcCdDeE") {
      events(
        dataType: Casts
        fightIDs: [3]
        sourceID: 42
        startTime: 0
        endTime: 9999999
        limit: 10000
        useAbilityIDs: true
      ) {
        nextPageTimestamp
        data
      }
    }
  }
}
```

### events Arguments

| Arg | Type | Description |
|-----|------|-------------|
| `dataType` | EventDataType | `Casts`, `DamageDone`, `Deaths`, `Buffs`, `Debuffs`, `Healing`, `All` |
| `fightIDs` | [Int] | Fights to include |
| `sourceID` | Int | Actor ID from masterData.actors |
| `targetID` | Int | Target actor ID |
| `abilityID` | Float | Filter to a specific spell ID |
| `startTime` | Float | Start offset in ms (relative to report) |
| `endTime` | Float | End offset in ms |
| `limit` | Int | Max events per page (max 10000) |
| `useAbilityIDs` | Boolean | Return ability IDs instead of names |
| `filterExpression` | String | WCL filter expression syntax |

### Pagination

If `nextPageTimestamp` is non-null, re-query with `startTime: nextPageTimestamp` to fetch
the next page. Repeat until `nextPageTimestamp` is null.

### Cast Event Shape
```json
{
  "timestamp": 14089632,
  "type": "cast",
  "sourceID": 42,
  "targetID": 78,
  "abilityGameID": 30451,
  "fight": 3
}
```

> **Note**: `events.data` is a JSON scalar (array of event objects). Parse with `json.loads()`.

---

## reportData — Table (Aggregated Damage)

Use `table` for pre-aggregated views instead of processing raw events.

```graphql
{
  reportData {
    report(code: "aAbBcCdDeE") {
      table(
        dataType: DamageDone
        fightIDs: [3]
        sourceID: 42
        translate: true
      )
    }
  }
}
```

**dataType options**: `DamageDone`, `Healing`, `DamageTaken`, `Casts`, `Buffs`, `Deaths`

---

## gameData — Classes and Specs

```graphql
{
  gameData {
    classes {
      id
      name
      specs {
        id
        name
      }
    }
  }
}
```

### Verified Class/Spec IDs (Midnight)

| Class | classID | Spec | specID |
|-------|---------|------|--------|
| Death Knight | 1 | Blood / Frost / Unholy | 1 / 2 / 3 |
| Druid | 2 | Balance / Feral / Guardian / Restoration | 1 / 2 / 3 / 4 |
| Hunter | 3 | Beast Mastery / Marksmanship / Survival | 1 / 2 / 3 |
| **Mage** | **4** | **Arcane / Fire / Frost** | **1 / 2 / 3** |
| Monk | 5 | Brewmaster / Mistweaver / Windwalker | 1 / 2 / 3 |
| Paladin | 6 | Holy / Protection / Retribution | 1 / 2 / 3 |
| Priest | 7 | Discipline / Holy / Shadow | 1 / 2 / 3 |
| Rogue | 8 | Assassination / Subtlety / Outlaw | 1 / 3 / 4 |
| Shaman | 9 | Elemental / Enhancement / Restoration | 1 / 2 / 3 |
| Warlock | 10 | Affliction / Demonology / Destruction | 1 / 2 / 3 |
| Warrior | 11 | Arms / Fury / Protection | 1 / 2 / 3 |
| Demon Hunter | 12 | Havoc / Vengeance / Devourer | 1 / 2 / 3 |
| Evoker | 13 | Devastation / Preservation / Augmentation | 1 / 2 / 3 |

> For `characterRankings` use string names (`className`, `specName`), not IDs.
> For event filtering and actor lookups, use the numeric `classID` / `specID`.

---

## rateLimitData — API Rate Limits

```graphql
{
  rateLimitData {
    limitPerHour
    pointsSpentThisHour
    pointsResetIn
  }
}
```

Each request costs points based on complexity. Check before bulk queries.

---

## Key Patterns for This Project

### Pattern 1: Fetch Top N Arcane Mage Parses on a Dungeon
```graphql
{
  worldData {
    encounter(id: 12874) {
      characterRankings(
        className: "Mage"
        specName: "Arcane"
        serverRegion: "US"
        difficulty: 10
        bracket: 18
        page: 1
        metric: dps
      )
    }
  }
}
```

### Pattern 2: Get a Player's Report Fights
```graphql
{
  reportData {
    report(code: "YOUR_CODE") {
      fights(killType: Kills) {
        id
        encounterID
        keystoneLevel
        startTime
        endTime
      }
      masterData(translate: true) {
        actors(type: "Player") {
          id
          name
          subType
        }
      }
    }
  }
}
```

### Pattern 3: Get Cast Events for a Specific Player + Fight
```graphql
{
  reportData {
    report(code: "YOUR_CODE") {
      events(
        dataType: Casts
        fightIDs: [FIGHT_ID]
        sourceID: PLAYER_ACTOR_ID
        limit: 10000
      ) {
        nextPageTimestamp
        data
      }
    }
  }
}
```

### Pattern 4: Fetch Competitor Casts (from their report code + fight ID)
Same as Pattern 3, using the `report.code` and `report.fightID` from the
`characterRankings` response.
