# CLAUDE.md — wow-wl-analyzer

## Project Purpose

A locally-runnable Python CLI tool that compares a player's Warcraft Logs Mythic+ performance
against top-ranked players of the same class/spec/dungeon. Currently scoped for Arcane Mage
Mythic+ Season 1 (WoW: Midnight), with a design that generalizes to any class/spec.

Target user: a competitive Mythic+ player who wants cast-level comparison data, not just a
percentile number.

## Sharability Constraints

- **Zero mandatory services**: users download, configure `.env`, run. No servers, no subscriptions.
- **Single Python entry point**: `python analyze.py` or equivalent — discoverable in 30 seconds.
- **`.env.example` always kept current**: every env var must appear there with a comment.
- **`requirements.txt` is pinned**: `pip install -r requirements.txt` must work cold.
- **No private credentials in source**: `.env` is in `.gitignore`; API keys are never hardcoded.

## Tech Stack

- **Language**: Python 3.10+
- **HTTP/GraphQL**: `requests` + raw GraphQL strings (no heavy client library)
- **Output**: terminal (rich/tabulate) + optional JSON export
- **Config**: `.env` loaded via `python-dotenv`
- **No framework**: this is a script, not a service

## WCL API

- **Endpoint**: `https://www.warcraftlogs.com/api/v2/client` (public, client credentials)
- **Auth**: OAuth2 client credentials — `POST /oauth/token` with `grant_type=client_credentials`
- **Docs**: `docs/wcl-api-spec.md` — canonical reference for all queries used in this project
- **Rate limits**: respect `rateLimitData`; default to one request per second unless the API
  signals otherwise
- **Never** commit `WCL_CLIENT_ID` or `WCL_CLIENT_SECRET` to source

## Key Domain Concepts

| Term | Meaning |
|------|---------|
| Parse | A single combat log submission; expressed as a percentile (e.g., 91%) |
| Keystone Level | Difficulty modifier for Mythic+ (e.g., +18) |
| Fight | One dungeon run within a report |
| Encounter ID | WCL's internal ID for a specific dungeon |
| Cast event | A single ability use recorded in the combat log |
| Arcane Mage class/spec | className="Mage", specName="Arcane", classID=4, specID=1 |

## Midnight Season 1 M+ Pool

Zone ID: **47** (`Mythic+ Season 1`)

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

## Code Quality Standards

- **No dead code**: if it's not used, it's not merged
- **No placeholder comments** (`# TODO: implement this`): either implement or don't add
- **Functions do one thing**: a function that fetches, parses, and prints is three functions
- **Errors are explicit**: raise with a message the user can act on, not a bare `except: pass`
- **No global state**: config and credentials are passed as parameters
- **Types**: use type hints on all function signatures

## Commit Conventions

Conventional Commits, scoped to the subsystem:

```
feat(auth): add OAuth token refresh
fix(query): handle paginated cast events correctly
chore(deps): pin requests to 2.32.0
docs(api): add characterRankings query example
```

Scope options: `auth`, `query`, `report`, `cli`, `deps`, `api`, `config`

## Iteration Model

1. Implement the smallest testable slice
2. Validate against the live WCL API (or a known report code)
3. Commit with a conventional commit message
4. Push

Do not batch multiple features into one commit. Do not write code for future iterations.

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `WCL_CLIENT_ID` | Your Warcraft Logs API client ID |
| `WCL_CLIENT_SECRET` | Your Warcraft Logs API client secret |
| `WCL_REPORT_CODE` | The report code to analyze (e.g., `aAbBcC123456`) |
| `TARGET_REGION` | Server region for rankings (default: `US`) |
| `TARGET_KEYSTONE_LEVEL` | Keystone level bracket to compare against (default: `18`) |
| `TOP_N_PARSES` | How many top parses to fetch for comparison (default: `10`) |
