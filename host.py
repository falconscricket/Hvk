import html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from gamestate import get_match, GameMode
from utils import is_host_or_owner, user_mention
from notify import notify_event, notify_bowler_turn

async def host_change_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    match = get_match(chat_id)
    if not match: return

    if not is_host_or_owner(match, user_id):
        await update.message.reply_text("⚠️ Only current host or bot owner can transfer host role.")
        return

    if not context.args:
        await update.message.reply_text("Usage: `/host_change <new_user_id>`")
        return

    new_host_id = int(context.args[0])
    match.host_id = new_host_id
    await update.message.reply_text(f"👑 Host updated to <code>{new_host_id}</code>.", parse_mode="HTML")

async def batting_assign_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    match = get_match(chat_id)
    if not match or not context.args: return

    if not is_host_or_owner(match, user_id):
        await update.message.reply_text("⚠️ Host access required.")
        return

    idx = int(context.args[0]) - 1  # 1-indexed to 0-indexed
    target_team = match.team_a if match.current_innings == 1 else match.team_b
    
    if 0 <= idx < len(target_team):
        match.current_batter = target_team[idx]
        await update.message.reply_text(f"✅ Host assigned Batter #{idx+1}: {user_mention(match.current_batter.user_id, match.current_batter.name)}", parse_mode="HTML")
        await notify_event(context.bot, chat_id, f"🏏 Next Batsman is {user_mention(match.current_batter.user_id, match.current_batter.name)}!")

async def bowling_assign_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    match = get_match(chat_id)
    if not match or not context.args: return

    if not is_host_or_owner(match, user_id):
        await update.message.reply_text("⚠️ Host access required.")
        return

    idx = int(context.args[0]) - 1
    target_team = match.team_b if match.current_innings == 1 else match.team_a
    
    if 0 <= idx < len(target_team):
        match.current_bowler = target_team[idx]
        await update.message.reply_text(f"✅ Host assigned Bowler #{idx+1}: {user_mention(match.current_bowler.user_id, match.current_bowler.name)}", parse_mode="HTML")
        await notify_bowler_turn(context.bot, chat_id, match.current_bowler.user_id, match.current_bowler.name)

async def toggle_pp_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    match = get_match(chat_id)
    if not match: return

    if not is_host_or_owner(match, update.effective_user.id):
        await update.message.reply_text("⚠️ Host access required.")
        return

    match.powerplay_active = not match.powerplay_active
    status = "ON 🔥 (+2 bonus runs on 4,5,6)" if match.powerplay_active else "OFF ⚪"
    await notify_event(context.bot, chat_id, f"⚡ <b>POWERPLAY IS NOW {status}</b>")
