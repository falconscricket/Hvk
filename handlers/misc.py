"""
handlers/misc.py — /start, /score, /end, /pp, /Feedback, and honest
"not yet available in this build" replies for the Team Match / Auction
commands that this delivery does not implement (see project README).
"""
from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from config import OWNER_IDS
from gamestate import GamePhase
from handlers.common import get_lock, get_match
from scoreboard import render_scoreboard


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.type == "private":
        await update.message.reply_text(
            "👋 Hi! Add me to a group and run /match (1v1) or /startgame (Solo Tournament) "
            "to start playing. When it's your turn to bowl, just type your number here."
        )
    else:
        await update.message.reply_text(
            "🏏 Hand Cricket Bot is ready! Use /match for a 1v1 game or /startgame for a "
            "Solo Tournament (4-30 players)."
        )


async def score_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    match = get_match(context, update.effective_chat.id)
    if match is None or match.phase not in (GamePhase.INNINGS_1, GamePhase.INNINGS_2):
        await update.message.reply_text("No live match in this chat right now.")
        return
    await update.message.reply_text(render_scoreboard(match), parse_mode="HTML")


async def end_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from handlers.common import announce_win
    match = get_match(context, update.effective_chat.id)
    user = update.effective_user
    if match is None or match.phase == GamePhase.COMPLETE:
        await update.message.reply_text("No active match to end.")
        return
    is_owner = user.id in OWNER_IDS
    if user.id != match.created_by and user.id != match.host_id and not is_owner:
        await update.message.reply_text("🚫 Only the match creator, Host, or an Owner can end it.")
        return
    async with get_lock(context, update.effective_chat.id):
        match.result_text = "🛑 Match ended manually by host/owner."
        await announce_win(context, match)


async def pp_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    match = get_match(context, update.effective_chat.id)
    user = update.effective_user
    if match is None or match.phase == GamePhase.COMPLETE:
        await update.message.reply_text("No active match in this chat.")
        return
    is_owner = user.id in OWNER_IDS
    if user.id != match.created_by and user.id != match.host_id and not is_owner:
        await update.message.reply_text("🚫 Only the match creator, Host, or an Owner can toggle Powerplay.")
        return
    async with get_lock(context, update.effective_chat.id):
        match.powerplay_active = not match.powerplay_active
        state = "ON ⚡" if match.powerplay_active else "OFF"
        await update.message.reply_text(f"Powerplay is now {state}.")


async def feedback_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = " ".join(context.args) if context.args else None
    if not text:
        await update.message.reply_text("Usage: /Feedback <your message>")
        return
    user = update.effective_user
    for owner_id in OWNER_IDS:
        if not owner_id:
            continue
        try:
            await context.bot.send_message(
                chat_id=owner_id,
                text=f"📝 Feedback from {user.first_name} (id={user.id}):\n{text}",
            )
        except Exception:
            pass
    await update.message.reply_text("✅ Thanks — your feedback was sent to the owners.")


async def not_yet_available(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Registered for the Team Match roster/host commands and the full Auction
    subsystem — both are out of scope for this build (see README)."""
    cmd = update.message.text.split()[0]
    await update.message.reply_text(
        f"⚠️ {cmd} is part of Team Match / Auction, which isn't implemented in this build yet. "
        f"1v1 (/match) and Solo Tournament (/startgame) are fully working."
    )
