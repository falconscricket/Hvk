import html
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import BOT_USERNAME, OWNER_IDS
from gamestate import MatchState

def user_mention(user_id: int, name: str) -> str:
    return f'<a href="tg://user?id={user_id}">{html.escape(name)}</a>'

def is_owner(user_id: int) -> bool:
    return user_id in OWNER_IDS

def is_host_or_owner(match: MatchState, user_id: int) -> bool:
    if is_owner(user_id):
        return True
    return match.host_id == user_id if match.host_id else False

def is_creator_or_owner(match: MatchState, user_id: int) -> bool:
    if is_owner(user_id):
        return True
    return match.creator_id == user_id

def build_bowling_pm_button(chat_id: int) -> InlineKeyboardMarkup:
    url = f"https://t.me/{BOT_USERNAME}?start=bowl_{chat_id}"
    return InlineKeyboardMarkup([[InlineKeyboardButton("🎳 Bowl Now (PM)", url=url)]])

def build_back_to_group_button(chat_id: int) -> InlineKeyboardMarkup:
    # Telegram internal chat link for return navigation
    clean_id = str(chat_id).replace("-100", "")
    url = f"https://t.me/c/{clean_id}"
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Group", url=url)]])

def build_batting_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(str(i), callback_data=f"bat_{i}") for i in range(0, 4)],
        [InlineKeyboardButton(str(i), callback_data=f"bat_{i}") for i in range(4, 7)]
    ]
    return InlineKeyboardMarkup(keyboard)

def build_bowling_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(str(i), callback_data=f"bowl_num_{i}") for i in range(0, 4)],
        [InlineKeyboardButton(str(i), callback_data=f"bowl_num_{i}") for i in range(4, 7)],
        [InlineKeyboardButton("W (Wide)", callback_data="bowl_num_W")]
    ]
    return InlineKeyboardMarkup(keyboard)
