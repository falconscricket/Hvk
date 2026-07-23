"""
owner.py — Hidden Owner PM command panel (/setmedia, /listmedia, /restart).
"""
from __future__ import annotations

import os
import sys

from telegram import Update
from telegram.ext import ContextTypes

from config import EVENT_KEY_DESCRIPTIONS, EVENT_KEYS, OWNER_IDS
from media import load_media_assets, save_media_asset


def is_owner(user_id: int) -> bool:
    return user_id in OWNER_IDS


async def setmedia_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_owner(user.id):
        await update.message.reply_text("🚫 Owner-only command.")
        return

    if not context.args:
        lines = ["📎 <b>Media Event Keys</b> — reply to a photo/GIF/video with "
                 "<code>/setmedia &lt;KEY&gt;</code> to bind it:\n"]
        for key in EVENT_KEYS:
            lines.append(f"• <b>{key}</b> — {EVENT_KEY_DESCRIPTIONS[key]}")
        await update.message.reply_text("\n".join(lines), parse_mode="HTML")
        return

    event_key = context.args[0].upper()
    if event_key not in EVENT_KEYS:
        await update.message.reply_text(
            f"⚠️ Unknown event key. Valid keys: {', '.join(EVENT_KEYS)}"
        )
        return

    replied = update.message.reply_to_message
    file_id = None
    media_type = None

    if replied:
        if replied.photo:
            file_id = replied.photo[-1].file_id
            media_type = "photo"
        elif replied.animation:
            file_id = replied.animation.file_id
            media_type = "animation"
        elif replied.video:
            file_id = replied.video.file_id
            media_type = "video"
    elif len(context.args) > 1:
        # Raw file_id passed directly: /setmedia FOUR <file_id> [photo|animation|video]
        file_id = context.args[1]
        media_type = context.args[2].lower() if len(context.args) > 2 else "photo"

    if not file_id:
        await update.message.reply_text(
            "⚠️ Reply to a photo/GIF/video with this command, or pass a raw file_id."
        )
        return

    await save_media_asset(event_key, file_id, media_type)
    await update.message.reply_text(f"✅ Media bound to <b>{event_key}</b>.", parse_mode="HTML")


async def listmedia_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_owner(user.id):
        await update.message.reply_text("🚫 Owner-only command.")
        return

    assets = await load_media_assets()
    lines = ["📋 <b>Media Status</b>"]
    for key in EVENT_KEYS:
        state = "✅ set" if assets.get(key) else "❌ not set"
        lines.append(f"• {key}: {state}")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def restart_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_owner(user.id):
        await update.message.reply_text("🚫 Owner-only command.")
        return
    await update.message.reply_text("♻️ Restarting…")
    os.execv(sys.executable, [sys.executable] + sys.argv)
