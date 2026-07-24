from telegram import Update
from telegram.ext import ContextTypes
from gamestate import get_match, remove_match
from scoreboard import render_scoreboard

async def score_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    match = get_match(chat_id)
    if not match:
        await update.message.reply_text("⚠️ No active match in this group.")
        return
    await update.message.reply_text(render_scoreboard(match), parse_mode="HTML")

async def end_match_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    match = get_match(chat_id)
    if not match: return
    remove_match(chat_id)
    await update.message.reply_text("🛑 Match terminated by host/owner command.")
