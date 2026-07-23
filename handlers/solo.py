"""
handlers/solo.py — Solo Tournament mode (4-30 players, automatic batting
order + bowler rotation, min-player auto-end, v5 Rule 2 lobby reminders).
"""
from __future__ import annotations

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

import match_engine
import notify
import timers
from config import OWNER_IDS, SOLO_TOURNAMENT_MAX_PLAYERS, SOLO_TOURNAMENT_MIN_PLAYERS
from gamestate import GameMode, GamePhase, InningsState, Match, Player
from handlers.common import (
    announce_win,
    get_lock,
    get_match,
    handle_batter_group_text,
    set_match,
    start_bowler_turn,
)
from utils import mention_html, over_length_buttons


async def startgame_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user
    existing = get_match(context, chat.id)
    if existing and existing.phase != GamePhase.COMPLETE:
        await update.message.reply_text("⚠️ A match is already active in this chat.")
        return

    match = Match(chat_id=chat.id, mode=GameMode.SOLO_TOURNAMENT, phase=GamePhase.LOBBY, created_by=user.id)
    match.players[user.id] = Player(user_id=user.id, first_name=user.first_name, username=user.username)
    set_match(context, match)

    await update.message.reply_text(
        f"🏆 Solo Tournament lobby opened by {mention_html(user.id, user.first_name)}!\n"
        f"/join to enter ({SOLO_TOURNAMENT_MIN_PLAYERS}-{SOLO_TOURNAMENT_MAX_PLAYERS} players). "
        f"Auto-starts in 2 minutes if the minimum is met.",
        parse_mode=ParseMode.HTML,
    )

    async def on_resolve(ctx: ContextTypes.DEFAULT_TYPE) -> None:
        async with get_lock(ctx, chat.id):
            m = get_match(ctx, chat.id)
            if m is None or m.phase != GamePhase.LOBBY:
                return
            if len(m.players) >= SOLO_TOURNAMENT_MIN_PLAYERS:
                await _begin_tournament(ctx, m)
            else:
                await ctx.bot.send_message(
                    chat_id=chat.id,
                    text=f"❌ Lobby auto-cancelled — only {len(m.players)} joined "
                         f"(need {SOLO_TOURNAMENT_MIN_PLAYERS}). Run /startgame again.",
                )
                m.phase = GamePhase.COMPLETE

    timers.start_tournament_lobby_timer(context, chat.id, on_resolve)


async def join_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user = update.effective_user
    match = get_match(context, chat_id)
    if match is None or match.mode != GameMode.SOLO_TOURNAMENT or match.phase != GamePhase.LOBBY:
        await update.message.reply_text("⚠️ No open Solo Tournament lobby right now.")
        return
    if user.id in match.players:
        await update.message.reply_text("You're already in.")
        return
    if len(match.players) >= SOLO_TOURNAMENT_MAX_PLAYERS:
        await update.message.reply_text("⚠️ Lobby is full (30 players max).")
        return

    async with get_lock(context, chat_id):
        match.players[user.id] = Player(user_id=user.id, first_name=user.first_name, username=user.username)
        await update.message.reply_text(
            f"✅ {mention_html(user.id, user.first_name)} joined! ({len(match.players)} players)",
            parse_mode=ParseMode.HTML,
        )


async def force_start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/force_start with /closelobby as an accepted alias."""
    chat_id = update.effective_chat.id
    user = update.effective_user
    match = get_match(context, chat_id)
    if match is None or match.mode != GameMode.SOLO_TOURNAMENT or match.phase != GamePhase.LOBBY:
        await update.message.reply_text("⚠️ No open Solo Tournament lobby right now.")
        return

    is_owner = user.id in OWNER_IDS
    if user.id != match.created_by and not is_owner:
        await update.message.reply_text("🚫 Only the lobby creator or an Owner can force-start.")
        return

    async with get_lock(context, chat_id):
        if len(match.players) < SOLO_TOURNAMENT_MIN_PLAYERS:
            await update.message.reply_text(
                f"⚠️ Need at least {SOLO_TOURNAMENT_MIN_PLAYERS} players to start (have {len(match.players)})."
            )
            return
        timers.cancel_existing_jobs(context, timers.lobby_timer_job_name(chat_id))
        await _begin_tournament(context, match)


async def _begin_tournament(context: ContextTypes.DEFAULT_TYPE, match: Match) -> None:
    order = list(match.players.keys())  # join order
    match.innings1 = InningsState(batting_order=order, bowling_order=order[::-1])
    match.phase = GamePhase.INNINGS_1

    await context.bot.send_message(
        chat_id=match.chat_id,
        text=f"🏁 Tournament starting with {len(order)} players! Batting order set by join order.",
    )
    await _prompt_over_length(context, match)


async def _prompt_over_length(context: ContextTypes.DEFAULT_TYPE, match: Match) -> None:
    bowler_id = match.current_bowler_id()
    bowler = match.players[bowler_id]
    await context.bot.send_message(
        chat_id=match.chat_id,
        text=f"{mention_html(bowler.user_id, bowler.first_name)}, choose your spell length:",
        parse_mode=ParseMode.HTML,
        reply_markup=over_length_buttons(match.chat_id, bowler_id),
    )


async def over_length_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    _, chat_id_s, bowler_id_s, length_s = query.data.split(":")
    chat_id, bowler_id, length = int(chat_id_s), int(bowler_id_s), int(length_s)
    match = get_match(context, chat_id)
    if match is None or match.mode != GameMode.SOLO_TOURNAMENT:
        await query.answer()
        return
    if query.from_user.id != bowler_id:
        await query.answer("Only the current bowler chooses this.", show_alert=True)
        return

    async with get_lock(context, chat_id):
        match.current_innings.over_length = length
        match.current_innings.balls_this_spell = 0
        await query.answer(f"Spell set to {length} ball(s).")
        await start_bowler_turn(context, match, bowler_id)


async def _rotate_or_continue_bowler(context: ContextTypes.DEFAULT_TYPE, match: Match) -> None:
    inn = match.current_innings
    if match_engine.check_bowler_rotation_due(inn):
        match_engine.advance_bowler(inn)
        new_bowler_id = match.current_bowler_id()
        if new_bowler_id is None:
            await _end_tournament(context, match, "No eligible bowlers remain.")
            return
        await _prompt_over_length(context, match)
    else:
        await start_bowler_turn(context, match, match.current_bowler_id())


async def _check_min_players(context: ContextTypes.DEFAULT_TYPE, match: Match) -> bool:
    """Returns True if the tournament was auto-ended due to falling below minimum eligible players."""
    if len(match.eligible_players()) < SOLO_TOURNAMENT_MIN_PLAYERS:
        await _end_tournament(context, match, "Active eligible players fell below the minimum (4).")
        return True
    return False


async def _end_tournament(context: ContextTypes.DEFAULT_TYPE, match: Match, reason: str) -> None:
    standings = sorted(match.players.values(), key=lambda p: p.runs, reverse=True)
    match.winner_id = standings[0].user_id if standings else None
    lines = [f"🏁 Tournament ended — {reason}", "", "📊 <b>Final Standings (by runs):</b>"]
    for i, p in enumerate(standings[:10], start=1):
        lines.append(f"{i}. {mention_html(p.user_id, p.first_name)} — {p.runs} runs, {p.wickets_taken} wkts")
    match.result_text = "\n".join(lines)
    await announce_win(context, match)


async def _on_wicket(context: ContextTypes.DEFAULT_TYPE, match: Match, batter_out_id: int) -> None:
    # Getting a player OUT removes them only from the current batting order —
    # never a match-end check on its own (Player-Count Integrity).
    inn = match.current_innings
    match_engine.advance_batter_after_wicket(inn)
    if await _check_min_players(context, match):
        return
    if match.current_batter_id() is None:
        await _end_tournament(context, match, "No eligible batters remain.")
        return
    await _rotate_or_continue_bowler(context, match)
    from handlers.common import start_batter_turn
    await start_batter_turn(context, match, match.current_batter_id())


async def _on_win_check(context: ContextTypes.DEFAULT_TYPE, match: Match, result) -> None:
    # Solo Tournament has no fixed target — it runs until min-player auto-end
    # or the host/Owner ends it manually; just continue rotation.
    await _rotate_or_continue_bowler(context, match)


async def batter_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    match = get_match(context, update.effective_chat.id)
    if match is None or match.mode != GameMode.SOLO_TOURNAMENT:
        return
    await handle_batter_group_text(update, context, _on_wicket, _on_win_check)


async def leave_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    match = get_match(context, chat_id)
    if match is None or match.mode != GameMode.SOLO_TOURNAMENT or match.phase == GamePhase.COMPLETE:
        return
    user = update.effective_user
    if user.id not in match.players:
        return

    async with get_lock(context, chat_id):
        match.players[user.id].eligible = False
        notify.clear_active_bowler(context, user.id)
        await update.message.reply_text(
            f"👋 {mention_html(user.id, user.first_name)} left the tournament.", parse_mode=ParseMode.HTML
        )
        await _check_min_players(context, match)
