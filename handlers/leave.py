from telegram import Update
from telegram.ext import ContextTypes
from gamestate import get_match, remove_match, GamePhase
from utils import user_mention

async def leave_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    match = get_match(chat_id)
    if not match: return

    user_id = update.effective_user.id
    
    if match.phase == GamePhase.LOBBY:
        match.solo_players = [p for p in match.solo_players if p.user_id != user_id]
        match.team_a = [p for p in match.team_a if p.user_id != user_id]
        match.team_b = [p for p in match.team_b if p.user_id != user_id]
        await update.message.reply_text(f"🚪 {user_mention(user_id, update.effective_user.first_name)} left the lobby.", parse_mode="HTML")
        if not match.solo_players and not match.team_a and not match.team_b:
            remove_match(chat_id)
