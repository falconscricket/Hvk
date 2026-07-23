"""
timers.py — JobQueue timer tasks: turn reminder/alert/foul, host inactivity
timeout, and tournament auto-start (with v5 Rule 2 lobby reminders).
"""
from __future__ import annotations

from telegram.constants import ParseMode
from telegram.ext import ContextTypes

import notify
from config import (
    FOUL_PENALTY_1ST,
    FOUL_PENALTY_2ND,
    SOLO_TOURNAMENT_MIN_PLAYERS,
    TOURNAMENT_LOBBY_SECONDS,
    TOURNAMENT_REMINDER_1_MARK,
    TOURNAMENT_REMINDER_2_MARK,
    TURN_TIMER_FOUL,
    TURN_TIMER_REMINDER_1,
    TURN_TIMER_REMINDER_2,
)
from utils import mention_html


def turn_timer_job_name(chat_id: int) -> str:
    return f"turn_timer:{chat_id}"


def lobby_timer_job_name(chat_id: int) -> str:
    return f"lobby_timer:{chat_id}"


def cancel_existing_jobs(context: ContextTypes.DEFAULT_TYPE, name: str) -> None:
    for job in context.job_queue.get_jobs_by_name(name):
        job.schedule_removal()


def start_turn_timer(context: ContextTypes.DEFAULT_TYPE, chat_id: int, offender_id: int,
                      offender_name: str, on_foul, is_batter: bool = False) -> None:
    """
    Schedules the 30s reminder, 50s alert, and 60s foul callback for the
    current turn-holder. `on_foul` is an async callback(context) invoked
    at the 60s mark that applies the actual penalty via match_engine/notify.
    """
    name = turn_timer_job_name(chat_id)
    cancel_existing_jobs(context, name)

    role = "bat" if is_batter else "bowl"

    async def _reminder_30(ctx: ContextTypes.DEFAULT_TYPE) -> None:
        await ctx.bot.send_message(
            chat_id=chat_id,
            text=f"⏳ {mention_html(offender_id, offender_name)}, 30s left to {role}!",
            parse_mode=ParseMode.HTML,
        )

    async def _alert_50(ctx: ContextTypes.DEFAULT_TYPE) -> None:
        await ctx.bot.send_message(
            chat_id=chat_id,
            text=f"🚨 {mention_html(offender_id, offender_name)}, final warning — 10s left to {role}!",
            parse_mode=ParseMode.HTML,
        )

    async def _foul_60(ctx: ContextTypes.DEFAULT_TYPE) -> None:
        await on_foul(ctx)

    context.job_queue.run_once(_reminder_30, when=TURN_TIMER_REMINDER_1, name=name, chat_id=chat_id)
    context.job_queue.run_once(_alert_50, when=TURN_TIMER_REMINDER_2, name=name, chat_id=chat_id)
    context.job_queue.run_once(_foul_60, when=TURN_TIMER_FOUL, name=name, chat_id=chat_id)


async def apply_foul(match, offender_id: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE,
                      re_notify_callback) -> None:
    """
    Shared foul-penalty logic (v4 Rule 3 compliant):
    - 1st foul: -6 (solo/1v1) / +6 opponent, penalty applied, and the SAME player
      must get a fresh explicit turn notification next time their turn cycles —
      handled by the caller via `re_notify_callback` when that turn comes back around.
    - 2nd foul: -12 escalated penalty, player removed from active list entirely,
      goes through the same Player-Count Integrity path as /leave.
    """
    player = match.players[offender_id]
    player.fouls += 1

    if player.fouls == 1:
        penalty = FOUL_PENALTY_1ST
        match.current_innings.total_runs = max(match.current_innings.total_runs - penalty, 0)
        await notify.notify_foul(context, chat_id, offender_id, player.first_name, penalty, 1)
        # Mark that this player needs a mandatory fresh notification the NEXT time
        # their turn comes around (not a silent re-arm).
        context.chat_data.setdefault("pending_foul_renotify", set()).add(offender_id)
    else:
        penalty = FOUL_PENALTY_2ND
        match.current_innings.total_runs = max(match.current_innings.total_runs - penalty, 0)
        player.eligible = False
        notify.clear_active_bowler(context, offender_id)
        await notify.notify_foul(context, chat_id, offender_id, player.first_name, penalty, 2)
        await notify.notify_removed_2nd_foul(context, chat_id, offender_id, player.first_name)


def start_tournament_lobby_timer(context: ContextTypes.DEFAULT_TYPE, chat_id: int,
                                  on_resolve) -> None:
    """
    2-minute auto-start/auto-cancel timer with v5 Rule 2 reminders at the
    1-minute and 30-second marks. Reminders fire regardless of which outcome
    the timer ultimately resolves to.
    """
    name = lobby_timer_job_name(chat_id)
    cancel_existing_jobs(context, name)

    delay_to_1min_mark = TOURNAMENT_LOBBY_SECONDS - TOURNAMENT_REMINDER_1_MARK
    delay_to_30s_mark = TOURNAMENT_LOBBY_SECONDS - TOURNAMENT_REMINDER_2_MARK

    async def _reminder_1min(ctx: ContextTypes.DEFAULT_TYPE) -> None:
        await ctx.bot.send_message(
            chat_id=chat_id,
            text="⏰ Lobby closing in 1 minute — /join now if you haven't!",
        )

    async def _reminder_30s(ctx: ContextTypes.DEFAULT_TYPE) -> None:
        await ctx.bot.send_message(
            chat_id=chat_id,
            text="⏰ Final call — lobby closes in 30 seconds!",
        )

    async def _resolve(ctx: ContextTypes.DEFAULT_TYPE) -> None:
        await on_resolve(ctx)

    context.job_queue.run_once(_reminder_1min, when=delay_to_1min_mark, name=name, chat_id=chat_id)
    context.job_queue.run_once(_reminder_30s, when=delay_to_30s_mark, name=name, chat_id=chat_id)
    context.job_queue.run_once(_resolve, when=TOURNAMENT_LOBBY_SECONDS, name=name, chat_id=chat_id)
