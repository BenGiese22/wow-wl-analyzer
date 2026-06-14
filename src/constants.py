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
