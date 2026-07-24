from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError
from utils import user_mention, build_bowling_pm_button
from media import media_manager

async def notify_event(
    bot: Bot, 
    chat_id: int, 
    text: str, 
    media_key: str | None = None, 
    reply_markup=None, 
    pm_user_id: int | None = None, 
    pm_text: str | None = None,
    pm_markup=None
):
    # Rule 4: Send media FIRST, then text as a separate message
    if media_key:
        file_id = media_manager.get_media(media_key)
        if file_id:
            try:
                await bot.send_photo(chat_id=chat_id, photo=file_id)
            except TelegramError:
                try:
                    await bot.send_animation(chat_id=chat_id, animation=file_id)
                except TelegramError:
                    pass

    # Public Group Notification
    if text:
        await bot.send_message(
            chat_id=chat_id, 
            text=text, 
            parse_mode=ParseMode.HTML, 
            reply_markup=reply_markup
        )

    # Private Message Dispatch
    if pm_user_id and pm_text:
        try:
            await bot.send_message(
                chat_id=pm_user_id, 
                text=pm_text, 
                parse_mode=ParseMode.HTML, 
                reply_markup=pm_markup
            )
        except TelegramError:
            pass

async def notify_bowler_turn(bot: Bot, chat_id: int, bowler_id: int, bowler_name: str):
    mention = user_mention(bowler_id, bowler_name)
    group_text = f"🎳 {mention}, it's your turn to bowl! Check PM."
    markup = build_bowling_pm_button(chat_id)
    
    await notify_event(
        bot=bot,
        chat_id=chat_id,
        text=group_text,
        reply_markup=markup,
        pm_user_id=bowler_id,
        pm_text=f"🏏 <b>It's your turn to bowl in chat {chat_id}!</b>\nPlease select your delivery below:"
    )

async def notify_batter_turn(bot: Bot, chat_id: int, batter_id: int, batter_name: str, keyboard):
    mention = user_mention(batter_id, batter_name)
    text = f"⚡ {mention}, bowler has locked delivery! Enter 0-6 in group or tap below. You have 60 seconds."
    await notify_event(bot=bot, chat_id=chat_id, text=text, reply_markup=keyboard)
