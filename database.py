"""
database.py — Persistent JSON storage manager for player stats.
(Media assets have their own dedicated store in media.py.)
"""
from __future__ import annotations

import json
import os
from typing import Any

import aiofiles

from config import DATA_DIR, PLAYER_STATS_FILE

_lock_file_init_done = False


def _ensure_data_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(PLAYER_STATS_FILE):
        with open(PLAYER_STATS_FILE, "w") as f:
            json.dump({}, f)


async def load_player_stats() -> dict[str, Any]:
    _ensure_data_dir()
    async with aiofiles.open(PLAYER_STATS_FILE, "r") as f:
        raw = await f.read()
    try:
        return json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return {}


async def save_player_stats(stats: dict[str, Any]) -> None:
    _ensure_data_dir()
    async with aiofiles.open(PLAYER_STATS_FILE, "w") as f:
        await f.write(json.dumps(stats, indent=2))


async def record_match_result(player_id: int, runs: int, wickets: int, won: bool) -> None:
    """Update a single player's cumulative career stats after a match ends."""
    stats = await load_player_stats()
    key = str(player_id)
    entry = stats.get(key, {"matches": 0, "runs": 0, "wickets": 0, "wins": 0})
    entry["matches"] += 1
    entry["runs"] += runs
    entry["wickets"] += wickets
    entry["wins"] += 1 if won else 0
    stats[key] = entry
    await save_player_stats(stats)
