"""
handlers/leave.py — Cross-mode /leave dispatcher. Routes to the correct
mode-specific leave handler based on the active match in this chat.
"""
from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from gamestate import GameMode
from handlers import onevone, solo
from handlers.common import get_match


async def leave_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    match = get_match(context, update.effective_chat.id)
    if match is None:
        await update.message.reply_text("You're not in an active match here.")
        return

    if match.mode == GameMode.ONE_V_ONE:
        await onevone.leave_command(update, context)
    elif match.mode == GameMode.SOLO_TOURNAMENT:
        await solo.leave_command(update, context)
    else:
        await update.message.reply_text(
            "⚠️ /leave for Team Match rosters isn't wired up in this build yet."
        )
