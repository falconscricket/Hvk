import html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from gamestate import get_match, create_match, remove_match, GameMode, GamePhase, Player
from utils import user_mention, is_owner, is_creator_or_owner, build_batting_keyboard
from notify import notify_event, notify_bowler_turn, notify_batter_turn
from match_engine import evaluate_delivery
from scoreboard import render_scoreboard

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    
    # Deep-link handling for Bowler PM
    if args and args[0].startswith("bowl_"):
        chat_id = int(args[0].replace("bowl_", ""))
        match = get_match(chat_id)
        if match and match.current_bowler and match.current_bowler.user_id == user.id:
            from utils import build_bowling_keyboard
            await update.message.reply_text("🎳 Choose your delivery:", reply_markup=build_bowling_keyboard())
            return

    await update.message.reply_text("🏏 <b>Welcome to Hand Cricket & Auction Bot!</b>\nUse /match, /startgame, or /join_a to begin.", parse_mode="HTML")

async def force_start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    match = get_match(chat_id)
    if not match or match.mode != GameMode.SOLO_TOURNAMENT: return

    if not is_creator_or_owner(match, update.effective_user.id):
        await update.message.reply_text("⚠️ Only tournament creator or bot owner can force start.")
        return

    if len(match.solo_players) < 4:
        await update.message.reply_text(f"⚠️ Need at least 4 players. Current: {len(match.solo_players)}")
        return

    match.phase = GamePhase.OVER_SELECTION
    await notify_event(context.bot, chat_id, "🚀 <b>Lobby Force Started!</b> Host selecting overs...")

async def general_text_and_button_delivery_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    match = get_match(chat_id)
    if not match or match.phase not in [GamePhase.INNINGS_1, GamePhase.INNINGS_2]:
        return

    user_id = update.effective_user.id
    
    # Handle Callback Button or Typed Text digit
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        if not query.data.startswith("bat_"): return
        bat_input = int(query.data.split("_")[1])
    else:
        text = update.message.text.strip()
        if not text.isdigit() or int(text) not in range(0, 7): return
        bat_input = int(text)

    if not match.current_batter or match.current_batter.user_id != user_id:
        return  # Ignore non-active batter inputs

    # Hat-trick restriction check
    if match.recent_bowler_wickets_consecutive >= 2 and bat_input == 0:
        await notify_event(
            context.bot, chat_id, 
            f"🎩 <b>Hat-trick ball!</b> {user_mention(user_id, match.current_batter.name)}, you can't play 0 here — pick a number 1-6."
        )
        return

    if match.pending_bowl_delivery is None:
        await notify_event(context.bot, chat_id, f"⚠️ Bowler hasn't delivered yet! {user_mention(user_id, match.current_batter.name)}, wait for PM lock.")
        return

    # Process delivery
    res = await evaluate_delivery(context.bot, match, bat_input)
    
    # Send Media then Commentary
    await notify_event(context.bot, chat_id, text=res["text"], media_key=res["media"])

    if res["match_ended"]:
        await notify_event(context.bot, chat_id, text="🏁 <b>FINAL MATCH SCOREBOARD</b>\n\n" + render_scoreboard(match))
        remove_match(chat_id)
