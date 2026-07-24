import logging
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters
)
from config import BOT_TOKEN
from database import db_manager
from media import media_manager
from owner import set_media_handler, restart_handler
from auction import add_cap_handler, start_auction_handler
from host import host_change_handler, batting_assign_handler, bowling_assign_handler, toggle_pp_handler
from handlers.common import start_command, force_start_handler, general_text_and_button_delivery_handler
from handlers.onevone import create_1v1_match, join_1v1_callback
from handlers.solo import start_tournament_lobby, join_tournament
from handlers.leave import leave_handler
from handlers.misc import score_command, end_match_command

logging.basicConfig(level=logging.INFO)

async def post_init(application):
    await db_manager.init_db()
    await media_manager.load_assets()
    logging.info("Database and Media assets successfully initialized.")

def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is missing in environment configuration.")

    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    # Owner Handlers
    app.add_handler(CommandHandler("setmedia", set_media_handler))
    app.add_handler(CommandHandler("restart", restart_handler))

    # General & Match Creation Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("match", create_1v1_match))
    app.add_handler(CommandHandler("startgame", start_tournament_lobby))
    app.add_handler(CommandHandler("force_start", force_start_handler))
    app.add_handler(CommandHandler("closelobby", force_start_handler))
    app.add_handler(CommandHandler("join", join_tournament))
    app.add_handler(CommandHandler("joingame", join_tournament))
    app.add_handler(CommandHandler("leave", leave_handler))
    app.add_handler(CommandHandler("score", score_command))
    app.add_handler(CommandHandler("end", end_match_command))
    app.add_handler(CommandHandler("end_match", end_match_command))

    # Host Controls
    app.add_handler(CommandHandler("host_change", host_change_handler))
    app.add_handler(CommandHandler("batting", batting_assign_handler))
    app.add_handler(CommandHandler("bowling", bowling_assign_handler))
    app.add_handler(CommandHandler("pp", toggle_pp_handler))

    # Auction Commands
    app.add_handler(CommandHandler("add_cap", add_cap_handler))
    app.add_handler(CommandHandler("start_auction", start_auction_handler))

    # Callbacks
    app.add_handler(CallbackQueryHandler(join_1v1_callback, pattern="^join_1v1$"))
    app.add_handler(CallbackQueryHandler(general_text_and_button_delivery_handler, pattern="^bat_"))

    # Digit / Text Delivery Listener
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, general_text_and_button_delivery_handler))

    logging.info("Bot started successfully!")
    app.run_polling()

if __name__ == "__main__":
    main()
