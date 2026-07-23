"""
handlers/common.py — Shared match registry, per-chat asyncio locks, and the
generic PM-bowling / group-batting delivery flow used by both 1v1 and Solo
Tournament modes.
"""
from __future__ import annotations

import asyncio
from typing import Optional

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

import match_engine
import notify
import timers
from config import EVENT_KEYS
from gamestate import GameMode, GamePhase, Match, Player
from scoreboard import render_scoreboard
from utils import mention_html, sanitize_batter_input, sanitize_bowler_input


def get_matches(context: ContextTypes.DEFAULT_TYPE) -> dict[int, Match]:
    return context.application.bot_data.setdefault("matches", {})


def get_match(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> Optional[Match]:
    return get_matches(context).get(chat_id)


def set_match(context: ContextTypes.DEFAULT_TYPE, match: Match) -> None:
    get_matches(context)[match.chat_id] = match


def get_lock(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> asyncio.Lock:
    locks = context.application.bot_data.setdefault("locks", {})
    if chat_id not in locks:
        locks[chat_id] = asyncio.Lock()
    return locks[chat_id]


async def _schedule_bowler_foul(context: ContextTypes.DEFAULT_TYPE, match: Match,
                                 bowler_id: int) -> None:
    async def on_foul(ctx: ContextTypes.DEFAULT_TYPE) -> None:
        async with get_lock(ctx, match.chat_id):
            await timers.apply_foul(match, bowler_id, match.chat_id, ctx, None)
            if match.players[bowler_id].eligible:
                # Same player must act again; timer restarts for the same ball.
                await _schedule_bowler_foul(ctx, match, bowler_id)
                timers.start_turn_timer(ctx, match.chat_id, bowler_id,
                                         match.players[bowler_id].first_name, on_foul, is_batter=False)

    timers.start_turn_timer(context, match.chat_id, bowler_id,
                             match.players[bowler_id].first_name, on_foul, is_batter=False)


def _pop_pending_foul_renotify(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    """v4 Rule 3: the first time a fouled player's turn cycles back, they must get a
    fresh, explicit turn notification — not a silent re-arm. Consumed exactly once."""
    pending = context.chat_data.setdefault("pending_foul_renotify", set())
    if user_id in pending:
        pending.discard(user_id)
        return True
    return False


async def start_bowler_turn(context: ContextTypes.DEFAULT_TYPE, match: Match, bowler_id: int) -> None:
    """Fires the mandatory group->PM handoff (v4 Rule 1) and (re)establishes
    PM routing (v4 Rule 2), then arms the turn timer. Automatically upgrades to
    the mandatory foul re-notification (v4 Rule 3) if this player owes one."""
    bowler = match.players[bowler_id]
    is_renotify = _pop_pending_foul_renotify(context, bowler_id)
    await notify.notify_bowler_turn(context, match.chat_id, bowler_id, bowler.first_name, is_renotify)
    await _schedule_bowler_foul(context, match, bowler_id)


async def start_batter_turn(context: ContextTypes.DEFAULT_TYPE, match: Match, batter_id: int) -> None:
    """Group-side turn start for the batter, also honoring the mandatory v4 Rule 3
    foul re-notification when this batter owes one."""
    batter = match.players[batter_id]
    is_renotify = _pop_pending_foul_renotify(context, batter_id)
    prefix = "⏱️ Your turn again — " if is_renotify else ""
    await context.bot.send_message(
        chat_id=match.chat_id,
        text=f"{prefix}{mention_html(batter_id, batter.first_name)}, your turn! Type a number 0-6 in the group.",
        parse_mode=ParseMode.HTML,
    )
    await _schedule_batter_foul(context, match, batter_id)


async def handle_bowler_pm_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Registered on private-chat text messages. Resolves which match (if any) this
    user is the current bowler for, regardless of when they opened the PM (v4 Rule 2)."""
    user = update.effective_user
    chat_id = notify.resolve_active_match_chat(context, user.id)
    if chat_id is None:
        return  # not currently anyone's bowling turn — not our concern

    match = get_match(context, chat_id)
    if match is None or match.phase not in (GamePhase.INNINGS_1, GamePhase.INNINGS_2):
        return

    if match.current_bowler_id() != user.id:
        return  # stale routing entry; ignore quietly

    async with get_lock(context, chat_id):
        inn = match.current_innings
        bowler = match.players[user.id]

        if inn.pending_bowler_input is not None:
            # Already locked this ball — v5 Rule 1: keep confirming, no new nav-button spam.
            await update.message.reply_text("✅ Already Bowled")
            return

        token = sanitize_bowler_input(update.message.text or "")
        if token is None:
            await update.message.reply_text("⚠️ Bowlers can't play 0. Enter 1-6 or W.")
            return

        timers.cancel_existing_jobs(context, timers.turn_timer_job_name(chat_id))

        if token == "W":
            batter_id = match.current_batter_id()
            batter = match.players[batter_id] if batter_id else None
            result = match_engine.resolve_delivery(match, bowler, batter, "W", None)
            await notify.notify_delivery_locked_pm(context, user.id, chat_id)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"↪️ WIDE! +{result.runs_added} run. {mention_html(bowler.user_id, bowler.first_name)} bowls again.",
                parse_mode=ParseMode.HTML,
            )
            await _send_scoreboard_and_media(context, match, chat_id, "WIDE")
            # Re-ball: same bowler, brand-new turn handoff (v4 Rule 1 applies every ball).
            await start_bowler_turn(context, match, bowler.user_id)
            return

        inn.pending_bowler_input = token
        await notify.notify_delivery_locked_pm(context, user.id, chat_id)

        batter_id = match.current_batter_id()
        await start_batter_turn(context, match, batter_id)


async def _schedule_batter_foul(context: ContextTypes.DEFAULT_TYPE, match: Match,
                                 batter_id: int) -> None:
    async def on_foul(ctx: ContextTypes.DEFAULT_TYPE) -> None:
        async with get_lock(ctx, match.chat_id):
            await timers.apply_foul(match, batter_id, match.chat_id, ctx, None)
            if match.players[batter_id].eligible:
                await _schedule_batter_foul(ctx, match, batter_id)
                timers.start_turn_timer(ctx, match.chat_id, batter_id,
                                         match.players[batter_id].first_name, on_foul, is_batter=True)

    timers.start_turn_timer(context, match.chat_id, batter_id,
                             match.players[batter_id].first_name, on_foul, is_batter=True)


async def handle_batter_group_text(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                    on_wicket, on_win_check) -> None:
    """
    Registered on group text messages. `on_wicket` and `on_win_check` are
    mode-specific callbacks (1v1 vs Solo Tournament) invoked after a
    delivery resolves, so each mode can apply its own end-of-innings /
    end-of-match rules on top of the shared engine.
    """
    chat_id = update.effective_chat.id
    match = get_match(context, chat_id)
    if match is None or match.phase not in (GamePhase.INNINGS_1, GamePhase.INNINGS_2):
        return

    inn = match.current_innings
    if inn.pending_bowler_input is None:
        return  # no ball currently in flight awaiting a batter

    batter_id = match.current_batter_id()
    if batter_id is None or update.effective_user.id != batter_id:
        return  # not this user's turn — leave regular chat alone

    forbid_zero = match_engine.hat_trick_zero_forbidden(inn)
    token = sanitize_batter_input(update.message.text or "", forbid_zero=forbid_zero)
    if token is None:
        if forbid_zero and (update.message.text or "").strip() == "0":
            await update.message.reply_text(
                "⚠️ You can't play 0 right after back-to-back wickets — enter 1-6."
            )
        else:
            await update.message.reply_text("⚠️ Enter a number 0-6.")
        return

    async with get_lock(context, chat_id):
        if inn.pending_bowler_input is None:
            return  # ball already resolved concurrently
        timers.cancel_existing_jobs(context, timers.turn_timer_job_name(chat_id))
        bowler_token = inn.pending_bowler_input
        inn.pending_bowler_input = None

        bowler = match.players[match.current_bowler_id()]
        batter = match.players[batter_id]
        result = match_engine.resolve_delivery(match, bowler, batter, bowler_token, token)

        event_key = None
        if result.wicket:
            event_key = "OUT"
        elif result.event.is_free_hit:
            event_key = "FREE_HIT"
        elif result.runs_added == 4:
            event_key = "FOUR"
        elif result.runs_added == 6:
            event_key = "SIX"
        elif result.runs_added == 0:
            event_key = "DOT"

        outcome_line = _describe_outcome(bowler, batter, bowler_token, token, result)
        await context.bot.send_message(chat_id=chat_id, text=outcome_line, parse_mode=ParseMode.HTML)

        if event_key:
            await _send_scoreboard_and_media(context, match, chat_id, event_key)
        else:
            await context.bot.send_message(chat_id=chat_id, text=render_scoreboard(match), parse_mode=ParseMode.HTML)

        if result.wicket:
            await on_wicket(context, match, batter.user_id)
        else:
            await on_win_check(context, match, result)


def _describe_outcome(bowler: Player, batter: Player, bowler_token: str, batter_token: str,
                       result) -> str:
    if result.wicket:
        return (f"🎯 OUT! {mention_html(batter.user_id, batter.first_name)} is out "
                f"({bowler_token} = {batter_token}). Bowler: "
                f"{mention_html(bowler.user_id, bowler.first_name)}")
    runs = result.runs_added
    free_hit_note = " 🆓 (Free Hit ball — no wicket possible)" if result.event.is_free_hit else ""
    return (f"🏏 {mention_html(batter.user_id, batter.first_name)} scored <b>{runs}</b> "
            f"run(s).{free_hit_note}")


async def _send_scoreboard_and_media(context: ContextTypes.DEFAULT_TYPE, match: Match,
                                      chat_id: int, event_key: str) -> None:
    import media as media_module
    await context.bot.send_message(chat_id=chat_id, text=render_scoreboard(match), parse_mode=ParseMode.HTML)
    await media_module.send_event_media(context.bot, chat_id, event_key)


async def announce_win(context: ContextTypes.DEFAULT_TYPE, match: Match) -> None:
    import media as media_module
    from scoreboard import render_result
    match.phase = GamePhase.COMPLETE
    await context.bot.send_message(chat_id=match.chat_id, text=render_result(match), parse_mode=ParseMode.HTML)
    await media_module.send_event_media(context.bot, match.chat_id, "WIN")
    for uid in list(notify._registry(context).keys()):
        if notify.resolve_active_match_chat(context, uid) == match.chat_id:
            notify.clear_active_bowler(context, uid)
    timers.cancel_existing_jobs(context, timers.turn_timer_job_name(match.chat_id))
