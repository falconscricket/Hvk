"""
utils.py — HTML formatting helpers, input sanitizers, user tags,
and navigation-only keyboard builders (never delivery-digit keyboards).
"""
from __future__ import annotations

from html import escape
from typing import Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, User

from config import BOT_USERNAME


def mention_html(user_id: int, name: str) -> str:
    """Build an HTML @mention that always resolves to the user, even without a username."""
    return f'<a href="tg://user?id={user_id}">{escape(name)}</a>'


def mention_from_user(user: User) -> str:
    return mention_html(user.id, user.first_name or user.username or str(user.id))


def sanitize_bowler_input(text: str) -> Optional[str]:
    """
    Returns a normalized bowler token ("1".."6" or "W"), or None if invalid.
    Bowlers may NEVER submit "0".
    """
    t = text.strip().upper()
    if t == "0":
        return None
    if t == "W":
        return "W"
    if t in {"1", "2", "3", "4", "5", "6"}:
        return t
    return None


def sanitize_batter_input(text: str, forbid_zero: bool = False) -> Optional[str]:
    """
    Returns a normalized batter token ("0".."6"), or None if invalid.
    forbid_zero=True enforces the hat-trick-ball restriction.
    """
    t = text.strip()
    if t not in {"0", "1", "2", "3", "4", "5", "6"}:
        return None
    if forbid_zero and t == "0":
        return None
    return t


def go_to_pm_button(bowler_name: str) -> InlineKeyboardMarkup:
    """Group -> PM navigation button (v4 Rule 1)."""
    url = f"https://t.me/{BOT_USERNAME}?start=bowl"
    return InlineKeyboardMarkup([[InlineKeyboardButton("🎯 Go to PM to Bowl", url=url)]])


def go_to_group_button(chat_id: int, message_id: Optional[int] = None) -> InlineKeyboardMarkup:
    """PM -> Group navigation button (v4 Rule 1). Uses a deep link back into the group if it
    has a public username; otherwise falls back to a generic label-only button."""
    # Telegram deep links to arbitrary private groups require an invite link or message link.
    # We use a message link when available (works for public groups/supergroups with usernames);
    # otherwise we still show the button pointing users to switch chats manually.
    if message_id is not None:
        url = f"https://t.me/c/{str(chat_id).replace('-100', '')}/{message_id}"
    else:
        url = f"https://t.me/{BOT_USERNAME}"
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Go to Group Chat", url=url)]])


def join_button(chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🙋 Join", callback_data=f"join:{chat_id}")]])


def over_length_buttons(chat_id: int, bowler_id: int) -> InlineKeyboardMarkup:
    """Structural buttons only — choosing spell length, never a delivery digit."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("1 Ball", callback_data=f"overlen:{chat_id}:{bowler_id}:1"),
        InlineKeyboardButton("3 Balls", callback_data=f"overlen:{chat_id}:{bowler_id}:3"),
    ]])


def im_host_button(chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("👑 I'm Host", callback_data=f"claimhost:{chat_id}")]])
