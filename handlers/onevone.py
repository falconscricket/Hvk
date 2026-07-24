from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from gamestate import get_match, create_match, GameMode, GamePhase, Player
from utils import user_mention
from notify import notify_event, notify_bowler_turn

async def create_1v1_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if get_match(chat_id):
        await update.message.reply_text("⚠️ A match is already running in this group!")
        return

    match = create_match(chat_id, GameMode.ONE_VS_ONE, update.effective_user.id)
    p1 = Player(user_id=update.effective_user.id, name=update.effective_user.first_name)
    match.team_a.append(p1)
    
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🎮 Join 1v1 Match", callback_data="join_1v1")]])
    await update.message.reply_text(
        f"🏏 1v1 Hand Cricket Match created by {user_mention(p1.user_id, p1.name)}!\nClick below to challenge!",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

async def join_1v1_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    user = query.from_user
    
    match = get_match(chat_id)
    if not match or match.phase != GamePhase.LOBBY: return

    if match.team_a[0].user_id == user.id:
        await query.answer("⚠️ You created this match!", show_alert=True)
        return

    p2 = Player(user_id=user.id, name=user.first_name)
    match.team_b.append(p2)
    match.phase = GamePhase.INNINGS_1
    
    # Default assign p1 as batter, p2 as bowler
    match.current_batter = match.team_a[0]
    match.current_bowler = match.team_b[0]
    
    await notify_event(
        context.bot, chat_id,
        f"⚔️ <b>Match Started!</b>\nBatter: {user_mention(match.current_batter.user_id, match.current_batter.name)}\nBowler: {user_mention(match.current_bowler.user_id, match.current_bowler.name)}"
    )
    await notify_bowler_turn(context.bot, chat_id, match.current_bowler.user_id, match.current_bowler.name)
