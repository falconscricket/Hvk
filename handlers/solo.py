from telegram import Update
from telegram.ext import ContextTypes
from gamestate import get_match, create_match, GameMode, GamePhase, Player
from utils import user_mention
from config import LOBBY_AUTOSTART_SECONDS

async def start_tournament_lobby(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if get_match(chat_id):
        await update.message.reply_text("⚠️ Match active already!")
        return

    match = create_match(chat_id, GameMode.SOLO_TOURNAMENT, update.effective_user.id)
    p = Player(user_id=update.effective_user.id, name=update.effective_user.first_name)
    match.solo_players.append(p)

    # Register 2m Auto-start timer
    context.job_queue.run_once(
        callback="autostart_lobby_callback",
        when=LOBBY_AUTOSTART_SECONDS,
        data={"chat_id": chat_id}
    )

    await update.message.reply_text(
        f"🏆 <b>Solo Tournament Lobby Opened!</b>\nJoin using `/join`. Auto-starts in 2 minutes!\n\n1. {user_mention(p.user_id, p.name)}",
        parse_mode="HTML"
    )

async def join_tournament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    match = get_match(chat_id)
    if not match or match.phase != GamePhase.LOBBY or match.mode != GameMode.SOLO_TOURNAMENT: return

    user = update.effective_user
    if any(p.user_id == user.id for p in match.solo_players):
        await update.message.reply_text("⚠️ You already joined!")
        return

    p = Player(user_id=user.id, name=user.first_name)
    match.solo_players.append(p)
    
    roster = "\n".join([f"{i+1}. {user_mention(pl.user_id, pl.name)}" for i, pl in enumerate(match.solo_players)])
    await update.message.reply_text(f"✅ {user_mention(user.id, user.first_name)} joined!\n\n<b>Current Lobby:</b>\n{roster}", parse_mode="HTML")
