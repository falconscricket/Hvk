"""
media.py — Dynamic media asset loader/manager (media_assets.json), plus
send_event_media() which actually dispatches media during live gameplay.
"""
from __future__ import annotations

import json
import os
from typing import Optional

import aiofiles
from telegram import Bot
from telegram.constants import ParseMode

from config import DATA_DIR, MEDIA_ASSETS_FILE, EVENT_KEYS


def _ensure_store() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(MEDIA_ASSETS_FILE):
        with open(MEDIA_ASSETS_FILE, "w") as f:
            json.dump({k: None for k in EVENT_KEYS}, f)


async def load_media_assets() -> dict[str, Optional[dict]]:
    """Returns {event_key: {"file_id": str, "type": "photo"|"animation"|"video"} | None}"""
    _ensure_store()
    async with aiofiles.open(MEDIA_ASSETS_FILE, "r") as f:
        raw = await f.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        data = {}
    for k in EVENT_KEYS:
        data.setdefault(k, None)
    return data


async def save_media_asset(event_key: str, file_id: str, media_type: str) -> None:
    assert event_key in EVENT_KEYS, f"Unknown event key: {event_key}"
    data = await load_media_assets()
    data[event_key] = {"file_id": file_id, "type": media_type}
    _ensure_store()
    async with aiofiles.open(MEDIA_ASSETS_FILE, "w") as f:
        await f.write(json.dumps(data, indent=2))


async def send_event_media(bot: Bot, chat_id: int, event_key: str, caption: Optional[str] = None) -> None:
    """
    Actually dispatch the configured media (if any) for the given event key
    into the given chat. Silently no-ops if no media is configured — the
    surrounding text notification always fires regardless.
    """
    assets = await load_media_assets()
    asset = assets.get(event_key)
    if not asset:
        return

    file_id = asset["file_id"]
    media_type = asset["type"]

    try:
        if media_type == "photo":
            await bot.send_photo(chat_id=chat_id, photo=file_id, caption=caption, parse_mode=ParseMode.HTML)
        elif media_type == "animation":
            await bot.send_animation(chat_id=chat_id, animation=file_id, caption=caption, parse_mode=ParseMode.HTML)
        elif media_type == "video":
            await bot.send_video(chat_id=chat_id, video=file_id, caption=caption, parse_mode=ParseMode.HTML)
    except Exception:
        # Media dispatch must never crash the match flow; the text notification already fired.
        pass
