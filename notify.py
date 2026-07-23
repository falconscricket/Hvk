"""
notify.py — Centralized notification dispatcher.

Every state-changing event fires a group-chat message AND, where relevant, a
PM to the affected player, always with an @mention and the mandatory
navigation button (v4 Rule 1) — never digit buttons.

This module ALSO owns the "active bowler PM routing" registry (v4 Rule 2):
the instant a player is assigned as the current bowler, we record
bot_data["active_bowler"][user_id] = chat_id. That mapping is what lets a
bowler's PM message resolve to the right match no matter when they opened
the bot's PM — before the match even started, or only once it became their
turn. The mapping is (re)written on every single bowler assignment, not just
the first toss.
"""
from __future__ import annotations

from typing import Optional

from telegram import Bot
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from utils import go_to_group_button, go_to_pm_button, mention_html


def _registry(context: ContextTypes.DEFAULT_TYPE) -> dict[int, int]:
    return context.application.bot_data.setdefault("active_bowler", {})


def register_active_bowler(context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int) -> None:
    """(Re)establish PM routing for this bowler. Call every time a bowler is (re)assigned,
    including foul re-cycles and rotations — not only at the first toss."""
    _registry(context)[user_id] = chat_id


def resolve_active_match_chat(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> Optional[int]:
    """Given a user_id who just messaged the bot's PM, find which chat's match they are
    the current bowler for — regardless of when they opened the PM."""
    return _registry(context).get(user_id)


def clear_active_bowler(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
    _registry(context).pop(user_id, None)


async def notify_bowler_turn(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    bowler_id: int,
    bowler_name: str,
    is_re_notification_after_foul: bool = False,
) -> None:
    """
    Group -> PM handoff (v4 Rule 1, mandatory on every single ball).
    Also used for the mandatory foul re-notification (v4 Rule 3) —
    same explicit "you bowl now" prompt, no silent re-arm.
    """
    register_active_bowler(context, bowler_id, chat_id)
    prefix = "⏱️ Your turn again — " if is_re_notification_after_foul else ""
    text = f"{prefix}{mention_html(bowler_id, bowler_name)}, it's your turn to bowl! Check PM."
    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=go_to_pm_button(bowler_name),
    )


async def notify_delivery_locked_pm(
    context: ContextTypes.DEFAULT_TYPE,
    bowler_pm_chat_id: int,
    group_chat_id: int,
    group_message_id: Optional[int] = None,
) -> None:
    """
    PM -> Group handoff (v4 Rule 1). Fired the instant a delivery locks.
    v5 Rule 1: confirmation text is "✅ Already Bowled" (replaces "✅ Delivery Locked").
    """
    await context.bot.send_message(chat_id=bowler_pm_chat_id, text="✅ Already Bowled")
    await context.bot.send_message(
        chat_id=bowler_pm_chat_id,
        text="Head back to the group to watch the result.",
        reply_markup=go_to_group_button(group_chat_id, group_message_id),
    )


async def notify_batter_turn(context: ContextTypes.DEFAULT_TYPE, chat_id: int,
                              batter_id: int, batter_name: str) -> None:
    text = f"{mention_html(batter_id, batter_name)}, your turn! Type a number 0-6 in the group."
    await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML)


async def notify_innings_change(context: ContextTypes.DEFAULT_TYPE, chat_id: int,
                                 batter_id: int, batter_name: str,
                                 bowler_id: int, bowler_name: str, target: int) -> None:
    register_active_bowler(context, bowler_id, chat_id)
    text = (f"🎯 <b>TARGET : {target} Runs</b>\n\n"
            f"Innings 2 begins! {mention_html(batter_id, batter_name)} is batting, "
            f"{mention_html(bowler_id, bowler_name)} is bowling.")
    await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML,
                                    reply_markup=go_to_pm_button(bowler_name))


async def notify_foul(context: ContextTypes.DEFAULT_TYPE, chat_id: int, offender_id: int,
                       offender_name: str, penalty_runs: int, foul_count: int) -> None:
    text = (f"⚠️ {mention_html(offender_id, offender_name)} took too long and committed "
            f"foul #{foul_count}! <b>-{penalty_runs} runs</b> penalty applied.")
    await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML)


async def notify_removed_2nd_foul(context: ContextTypes.DEFAULT_TYPE, chat_id: int,
                                   offender_id: int, offender_name: str) -> None:
    text = (f"🚫 {mention_html(offender_id, offender_name)} committed a 2nd foul and has been "
            f"removed from the match.")
    await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML)


async def notify_host_action(context: ContextTypes.DEFAULT_TYPE, chat_id: int, host_id: int,
                              host_name: str, action_description: str) -> None:
    text = f"👑 {mention_html(host_id, host_name)} {action_description}"
    await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML)
    try:
        await context.bot.send_message(chat_id=host_id, text=f"Confirmed: {action_description}")
    except Exception:
        pass  # host may not have a PM session open; group confirmation already fired
