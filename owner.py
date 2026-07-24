import sys
import os
from telegram import Update
from telegram.ext import ContextTypes
from utils import is_owner
from media import media_manager

async def set_media_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private" or not is_owner(update.effective_user.id):
        return  # Owner PM Only

    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Usage: `/setmedia <FOUR|SIX|DOT|OUT|FREE_HIT|WIDE|WIN> <file_id>`", parse_mode="Markdown")
        return

    event_key = context.args[0].upper()
    file_id = context.args[1]
    
    valid_keys = ["FOUR", "SIX", "DOT", "OUT", "FREE_HIT", "WIDE", "WIN"]
    if event_key not in valid_keys:
        await update.message.reply_text(f"⚠️ Invalid key. Allowed: {', '.join(valid_keys)}")
        return

    await media_manager.set_media(event_key, file_id)
    await update.message.reply_text(f"✅ Custom media set for <b>{event_key}</b>!", parse_mode="HTML")

async def restart_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private" or not is_owner(update.effective_user.id):
        return

    await update.message.reply_text("🔄 Rebooting Telegram Hand Cricket Bot...")
    os.execl(sys.executable, sys.executable, *sys.argv)
