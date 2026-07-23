"""
bot.py — Main entry point. Application setup, JobQueue setup, handler registration.
"""
from __future__ import annotations

import logging

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import BOT_TOKEN
from handlers import leave, misc, onevone, solo
from handlers.common import handle_bowler_pm_text
import owner

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Commands from the spec's mandatory registration list that this build does not
# implement (Team Match rosters / full Auction subsystem). Registered honestly
# rather than left to fall through as "unknown command".
NOT_YET_AVAILABLE_COMMANDS = [
    "joingame", "join_a", "join_b", "add_A", "add_B", "remove_A", "remove_B",
    "batting", "bowling", "swap", "host_change",
    "add_cap", "rm_cap", "cap_change_auction", "auction_id", "start_auction",
    "pause_auction", "resume_auction", "auction_host_change", "xp", "unsold",
    "rm_auction_id",
]


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Unhandled exception while processing update: %s", update, exc_info=context.error)


def build_application() -> Application:
    application = Application.builder().token(BOT_TOKEN).build()

    # --- Core / shared ---
    application.add_handler(CommandHandler("start", misc.start_command))
    application.add_handler(CommandHandler("score", misc.score_command))
    application.add_handler(CommandHandler("end", misc.end_command))
    application.add_handler(CommandHandler("end_match", misc.end_command))
    application.add_handler(CommandHandler("pp", misc.pp_command))
    application.add_handler(CommandHandler("Feedback", misc.feedback_command, filters.COMMAND))
    application.add_handler(CommandHandler("leave", leave.leave_command))

    # --- 1v1 ---
    application.add_handler(CommandHandler("match", onevone.match_command))
    application.add_handler(CallbackQueryHandler(onevone.join_callback, pattern=r"^1v1join:"))

    # --- Solo Tournament ---
    application.add_handler(CommandHandler("startgame", solo.startgame_command))
    application.add_handler(CommandHandler("join", solo.join_command))
    application.add_handler(CommandHandler("force_start", solo.force_start_command))
    application.add_handler(CommandHandler("closelobby", solo.force_start_command))  # alias
    application.add_handler(CallbackQueryHandler(solo.over_length_callback, pattern=r"^overlen:"))

    # --- Owner panel (PM only, enforced inside the handlers themselves) ---
    application.add_handler(CommandHandler("setmedia", owner.setmedia_command))
    application.add_handler(CommandHandler("listmedia", owner.listmedia_command))
    application.add_handler(CommandHandler("restart", owner.restart_command))

    # --- Honest stubs for out-of-scope spec commands ---
    for cmd in NOT_YET_AVAILABLE_COMMANDS:
        application.add_handler(CommandHandler(cmd, misc.not_yet_available))

    # --- Delivery text flow ---
    # PM bowler input — routes via the active-bowler registry (v4 Rule 2), so it
    # works no matter when the bowler opened the PM.
    application.add_handler(
        MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, handle_bowler_pm_text)
    )
    # Group batter input — each mode's handler checks whether the match in this
    # chat is actually its mode before doing anything.
    application.add_handler(
        MessageHandler(filters.ChatType.GROUPS & filters.TEXT & ~filters.COMMAND, onevone.batter_text_handler)
    )
    application.add_handler(
        MessageHandler(filters.ChatType.GROUPS & filters.TEXT & ~filters.COMMAND, solo.batter_text_handler)
    )

    application.add_error_handler(on_error)
    return application


def main() -> None:
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN is not set — copy .env.example to .env and fill it in.")
    application = build_application()
    logger.info("Starting Hand Cricket bot…")
    application.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
