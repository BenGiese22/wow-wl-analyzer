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

    git clone https://github.com/BenGiese22/wow-wl-analyzer.git
    cd wow-wl-analyzer
    pip install -r requirements.txt
    python analyze.py setup

`setup` will prompt for your API credentials and character, validate them, and save everything to `.env`.

## Usage

### Season overview

    python analyze.py overview --report <your-report-code>
    # Optional: --top 10 --bracket 18

### Dungeon breakdown

    python analyze.py dungeon --report <code> --dungeon "Maisara Caverns" --bracket 18
    # Optional: --top 10

### 1v1 comparison

    python analyze.py compare --report <your-code> --fight <your-fight-id> \
      --vs <their-report-code> --vs-fight <their-fight-id>

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
