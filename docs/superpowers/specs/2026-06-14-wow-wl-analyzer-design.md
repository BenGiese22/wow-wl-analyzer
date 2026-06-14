# wow-wl-analyzer — Design Spec

**Date:** 2026-06-14
**Author:** Benjamin Giese (BenGiese22)
**Status:** Approved

---

## Problem

Top 60 world Arcane Mage players want to close the gap to world-first-level performance. Warcraft
Logs exposes the raw data needed for cast-level comparison, but there is no tool that takes a
player's own report and directly compares their ability usage to the top parses of the same
class/spec/dungeon. The only existing insight is a percentile number — not actionable gameplay
guidance.

The concrete example that motivated this: a player discovered a competitor used Arcane Pulse over
Arcane Blast 8.7% more — a meaningful rotation difference that a percentile alone would never
surface.

---

## Goals

- Compare a player's cast-level data against top-N ranked players for the same class/spec/dungeon
- Surface the specific ability deltas that explain the performance gap
- Run fully locally with minimal setup (download → configure → run)
- Be sharable as a GitHub repo with no mandatory external services
- Generate both a quick terminal summary and a detailed HTML report

---

## Non-Goals (v1)

- No web server or hosted service
- No AI-powered analysis (noted as a future iteration)
- No real-time tracking or live log parsing
- No support for raid content (Mythic+ only, v1)
- No interactive UI (Python CLI now; UI is a future layer on top of this logic)

---

## Tech Stack

| Concern | Choice | Rationale |
|---------|--------|-----------|
| Language | Python 3.10+ | Widest local sharability, excellent for data, no compile step |
| HTTP | `requests` | Simple, reliable, no heavy GraphQL client needed |
| Config | `python-dotenv` | Standard `.env` pattern, easy to document |
| Terminal output | `rich` | Tables, colors, progress spinners without fighting ANSI |
| HTML report | Inline template string (no framework) | Zero build step, single file output |
| Dependencies | `requirements.txt` (pinned) | Cold install must work: `pip install -r requirements.txt` |

---

## Architecture

```
wow-wl-analyzer/
├── analyze.py          # Entry point — all subcommands
├── requirements.txt
├── .env.example
├── .gitignore
├── CLAUDE.md
├── src/
│   ├── auth.py         # OAuth token acquisition + caching
│   ├── client.py       # GraphQL request wrapper
│   ├── queries.py      # All GraphQL query strings
│   ├── character.py    # Character lookup + class/spec resolution
│   ├── rankings.py     # Top-N parse fetching + report code extraction
│   ├── events.py       # Cast event fetching + pagination
│   ├── comparison.py   # Delta calculation between player and top-N
│   └── report.py       # Terminal output + HTML report generation
└── docs/
    ├── wcl-api-spec.md
    └── superpowers/specs/
```

Each module has one clear responsibility. `analyze.py` wires them together per subcommand —
it does not contain business logic.

---

## CLI Interface

Single entry point, three analysis subcommands plus setup:

```bash
python analyze.py setup
python analyze.py overview  --report <code> [--top N] [--bracket N]
python analyze.py dungeon   --report <code> --dungeon <name> --bracket N [--top N]
python analyze.py compare   --report <code> --fight <id> --vs <report> --vs-fight <id>
```

All flags that have a `.env` default can be omitted. CLI args override `.env` values.

---

## Setup Command

`python analyze.py setup` runs once (or to reconfigure). Interactive prompts, saved to `.env`.

### Flow

1. Print link to WCL client creation page
2. Prompt for `WCL_CLIENT_ID` and `WCL_CLIENT_SECRET` (secret masked with `getpass`)
3. Validate credentials against the live API — fail fast with a clear message if invalid
4. Prompt for character name, realm, region (default: US)
5. Look up character via `characterData` API — confirm class/spec back to user
6. Prompt for `TOP_N_PARSES` (default: 10) and `DEFAULT_BRACKET` (default: 18)
7. Write `.env` with all values; confirm what was saved

### Character Name Handling

WoW character names allow accented and diacritical characters (e.g., `Bêngi`, `Æthon`).
All character name I/O must be treated as UTF-8:
- `input()` returns a Unicode string in Python 3 — no special handling needed for stdin
- `.env` must be written with `encoding="utf-8"` explicitly
- `.env` must be read with `encoding="utf-8"` explicitly (do not rely on system default)
- API requests send names as JSON strings via `requests` — UTF-8 encoded automatically
- Terminal output via `rich` handles Unicode correctly on modern terminals

### `.env` Schema

```dotenv
# WCL API credentials
WCL_CLIENT_ID=
WCL_CLIENT_SECRET=

# Your character (class/spec resolved at setup time and cached)
CHARACTER_NAME=
CHARACTER_REALM=
CHARACTER_REGION=US
CHARACTER_CLASS=
CHARACTER_SPEC=

# Analysis defaults (overridable per command)
TOP_N_PARSES=10
DEFAULT_BRACKET=18
```

---

## Three-Tier Analysis Model

### Tier 1 — Season Overview (`overview`)

**Scope:** All dungeons in the player's report(s), compared against top-N for each.

**Inputs:** Report code, top N, keystone bracket.

**What it computes:**
- Per-dungeon: player DPS, top-N avg DPS, parse percentile, DPS gap vs top-N
- Which dungeons show the largest performance gap (by DPS% and parse percentile)

**Data source:** `characterRankings` DPS figures only — no cast event fetching at this tier.
Ability-level deltas require Tier 2 (`dungeon` command) which fetches cast events.

**Terminal output:** One block per dungeon — parse %, your DPS vs top-N avg, DPS gap. No
ability breakdown (that's Tier 2).

**HTML output:** Parse-by-dungeon cards with color-coded bars and DPS gap. Prompt to drill
into a specific dungeon for ability-level detail.

---

### Tier 2 — Dungeon Breakdown (`dungeon`)

**Scope:** One specific dungeon at a specific keystone level, player's best run vs top-N avg.

**Keystone level matching is mandatory.** Mob HP and pack composition change enough between
levels that a +18 vs +20 comparison is not meaningful. Both the player's run and the top-N
comparison pool must be filtered to the same keystone level bracket.

- Player side: filter their report's fights to `encounterID` + `keystoneLevel == bracket`,
  then select the highest-DPS completed kill among those.
- Comparison side: `characterRankings(bracket: N)` filters the WCL leaderboard to that level.

If the player has no completed kill at the specified bracket for that dungeon, exit with a
clear message: "No +{bracket} kill found for {dungeon} in report {code}."

**Inputs:** Report code, dungeon name, bracket (keystone level), top N.

**What it computes:**
- Per-ability: cast count (player vs top-N avg), damage per cast, % of total GCDs
- Delta per ability (count and GCD%)
- Top-2 actionable findings (biggest negative deltas = most addressable gaps)

**Terminal output:** Full ability table (cast count, dmg/cast, delta, GCD%). All abilities shown.

**HTML output:** Key findings insight boxes + full ability table with GCD% columns.

**Note on GCD%:** Raw cast counts are misleading when run durations differ. GCD% (share of
total global cooldowns spent on each ability) normalizes for run length and is the primary
comparison metric.

---

### Tier 3 — 1v1 Player Comparison (`compare`)

**Scope:** Player's specific fight vs one specific competitor's fight. Cast-for-cast.

**Inputs:** Player's report code + fight ID; competitor's report code + fight ID.
Competitor report codes come from the `characterRankings` response surfaced in Tier 1/2.

**What it computes:**
- Side-by-side cast count per ability
- Per-ability damage per cast (both players)
- Red/green highlighting of meaningful differences

**Terminal output:** Two-column side-by-side cast table.

**HTML output:** Side-by-side player columns with per-ability rows, red/green on deltas.

---

## Output

### Terminal

- Tier 1: Section per dungeon, top deltas only (concise, fast to read)
- Tier 2: Full ability table including GCD% columns
- Tier 3: Side-by-side two-column cast count table
- All tiers: Path to generated HTML file printed at the end

### HTML Report

- Dark WoW-themed stylesheet (inline, no external dependencies)
- Three tabs: Season Overview / Dungeon Breakdown / 1v1 Compare
- Season Overview: parse-by-dungeon cards + aggregate ability delta table
- Dungeon Breakdown: key findings insight boxes + full ability table
- 1v1 Compare: side-by-side player columns
- Saved to `output/report_YYYY-MM-DD_HH-MM.html`
- `output/` is in `.gitignore`

---

## Data Flow

```
setup
  └── characterData(name, realm, region) → class, spec → .env

overview / dungeon
  ├── reportData(code)
  │     └── fights(killType: Kills) → fight list + encounterIDs
  ├── worldData.encounter(id).characterRankings(class, spec, region, bracket, page)
  │     └── top-N rankings → [{ report.code, report.fightID, name, amount }]
  ├── reportData(code).events(dataType: Casts, fightIDs, sourceID) [paginated]
  │     └── player cast events → { abilityID → count }
  ├── reportData(competitor_code).events(...) [for each top-N player]
  │     └── competitor cast events → { abilityID → count }
  └── comparison.py → delta table → terminal + HTML

compare
  ├── reportData(my_code).events(fightIDs: [my_fight], dataType: Casts, sourceID)
  ├── reportData(their_code).events(fightIDs: [their_fight], dataType: Casts)
  └── comparison.py → side-by-side → terminal + HTML
```

---

## Error Handling

- Invalid credentials at setup: clear message with link to WCL client page
- Character not found: suggest checking name spelling and realm (note: accented characters must match exactly)
- Report code not found / private report: inform user and suggest making report public
- API rate limit hit: surface `rateLimitData.pointsResetIn`, wait or exit gracefully
- Empty rankings for class/spec/dungeon/bracket: inform user (may mean no parses exist at that bracket)
- Paginated events: loop until `nextPageTimestamp` is null — never silently truncate

---

## Sharability Checklist

- [ ] `README.md` covers: prerequisites, setup, all three commands, example output
- [ ] `.env.example` has every variable with a comment
- [ ] `requirements.txt` is pinned
- [ ] No credentials in source, ever
- [ ] `python analyze.py setup` is the only onboarding step needed
- [ ] Works on macOS, Linux, Windows (Python 3.10+)

---

## Future Considerations (not in scope for v1)

- AI-powered analysis: feed the delta table to a model for natural-language rotation advice
- React/web UI: the `src/` modules become a backend; the UI consumes them
- Multi-character support: save multiple characters, switch with `--character`
- Raid support: extend encounter ID mapping and ability sets
- Cast ordering / sequence analysis: not just count but *when* in the pull each ability was pressed
