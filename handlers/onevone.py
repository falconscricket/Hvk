"""
handlers/onevone.py — 1v1 Normal Match mode.
"""
from __future__ import annotations

import random

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

import notify
from gamestate import GameMode, GamePhase, InningsState, Match, Player
from handlers.common import (
    announce_win,
    get_lock,
    get_match,
    handle_batter_group_text,
    set_match,
    start_bowler_turn,
)
from utils import mention_html


async def match_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user
    existing = get_match(context, chat.id)
    if existing and existing.phase != GamePhase.COMPLETE:
        await update.message.reply_text("⚠️ A match is already active in this chat.")
        return

    match = Match(chat_id=chat.id, mode=GameMode.ONE_V_ONE, phase=GamePhase.LOBBY, created_by=user.id)
    match.players[user.id] = Player(user_id=user.id, first_name=user.first_name, username=user.username)
    set_match(context, match)

    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🙋 Join as Player 2", callback_data=f"1v1join:{chat.id}")]])
    await update.message.reply_text(
        f"🏏 {mention_html(user.id, user.first_name)} started a 1v1 Hand Cricket match! Who's in?",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )


async def join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    chat_id = int(query.data.split(":")[1])
    match = get_match(context, chat_id)
    user = query.from_user

    if match is None or match.mode != GameMode.ONE_V_ONE or match.phase != GamePhase.LOBBY:
        await query.answer("This match is no longer accepting players.", show_alert=True)
        return
    if user.id in match.players:
        await query.answer("You already joined.", show_alert=True)
        return

    async with get_lock(context, chat_id):
        match.players[user.id] = Player(user_id=user.id, first_name=user.first_name, username=user.username)
        await query.answer("Joined!")
        await _start_toss(context, match)


async def _start_toss(context: ContextTypes.DEFAULT_TYPE, match: Match) -> None:
    match.phase = GamePhase.TOSS
    ids = list(match.players.keys())
    random.shuffle(ids)
    bowler_id, batter_id = ids[0], ids[1]

    match.innings1 = InningsState(
        batting_order=[batter_id, bowler_id],
        bowling_order=[bowler_id, batter_id],
        over_length=9999,  # bowler never rotates mid-innings in 1v1
    )
    match.innings2 = InningsState(over_length=9999)
    match.phase = GamePhase.INNINGS_1

    bowler = match.players[bowler_id]
    batter = match.players[batter_id]
    await context.bot.send_message(
        chat_id=match.chat_id,
        text=(f"🪙 Toss done! {mention_html(batter.user_id, batter.first_name)} bats first, "
              f"{mention_html(bowler.user_id, bowler.first_name)} bowls first."),
        parse_mode=ParseMode.HTML,
    )
    await start_bowler_turn(context, match, bowler_id)


async def _on_wicket(context: ContextTypes.DEFAULT_TYPE, match: Match, batter_out_id: int) -> None:
    if match.innings_no == 1:
        target = match.innings1.total_runs
        old_bowler_id = match.current_bowler_id()
        old_batter_id = batter_out_id
        # Innings 2: roles swap.
        match.innings_no = 2
        match.innings2.target = target + 1
        match.innings2.batting_order = [old_bowler_id, old_batter_id]
        match.innings2.bowling_order = [old_batter_id, old_bowler_id]
        match.phase = GamePhase.INNINGS_2

        new_batter = match.players[old_bowler_id]
        new_bowler = match.players[old_batter_id]
        await notify.notify_innings_change(context, match.chat_id, new_batter.user_id, new_batter.first_name,
                                            new_bowler.user_id, new_bowler.first_name, match.innings2.target)
        await start_bowler_turn(context, match, new_bowler.user_id)
    else:
        inn = match.innings2
        batter_score_before_out = inn.total_runs
        if batter_score_before_out == inn.target - 1:
            match.result_text = "🤝 Match DRAWN — batter was out one run short of the target!"
        else:
            match.result_text = "🎯 Bowler wins — batter dismissed before reaching the target!"
            match.winner_id = match.current_bowler_id()
        await announce_win(context, match)


async def _on_win_check(context: ContextTypes.DEFAULT_TYPE, match: Match, result) -> None:
    if match.innings_no == 2 and result.match_ended:
        match.result_text = "🏆 Batter wins — target chased down!"
        match.winner_id = match.current_batter_id()
        await announce_win(context, match)


async def batter_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    match = get_match(context, update.effective_chat.id)
    if match is None or match.mode != GameMode.ONE_V_ONE:
        return
    await handle_batter_group_text(update, context, _on_wicket, _on_win_check)


async def leave_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    match = get_match(context, chat_id)
    if match is None or match.mode != GameMode.ONE_V_ONE or match.phase == GamePhase.COMPLETE:
        return
    user = update.effective_user
    if user.id not in match.players:
        return

    async with get_lock(context, chat_id):
        opponent_id = next((uid for uid in match.players if uid != user.id), None)
        match.result_text = f"🚩 {mention_html(user.id, user.first_name)} left the match — walkover!"
        match.winner_id = opponent_id
        await announce_win(context, match)
