"""
config.py — Configuration variables for the Hand Cricket bot.
All values are loaded from environment variables (see .env.example).
"""
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

# Dual owners — both act as implicit Host/Captain/tournament-creator everywhere.
OWNER_ID_1: int = int(os.getenv("OWNER_ID_1", "0"))
OWNER_ID_2: int = int(os.getenv("OWNER_ID_2", "0"))
OWNER_IDS: set[int] = {OWNER_ID_1, OWNER_ID_2}

# Bot username (without @) — required to build PM deep-link buttons.
BOT_USERNAME: str = os.getenv("BOT_USERNAME", "")

# --- Timers (seconds) ---
TURN_TIMER_REMINDER_1 = 30     # first reminder
TURN_TIMER_REMINDER_2 = 50     # final alert
TURN_TIMER_FOUL = 60           # timeout -> foul

TOURNAMENT_LOBBY_SECONDS = 120  # 2-minute auto-start/auto-cancel window
TOURNAMENT_REMINDER_1_MARK = 60   # fires when 60s remain (the "1-minute mark")
TOURNAMENT_REMINDER_2_MARK = 30   # fires when 30s remain (the "30-second mark")

HOST_INACTIVITY_SECONDS = 120

# --- Gameplay constants ---
SOLO_TOURNAMENT_MIN_PLAYERS = 4
SOLO_TOURNAMENT_MAX_PLAYERS = 30

FOUL_PENALTY_1ST = 6    # runs deducted from offender / awarded to opponent
FOUL_PENALTY_2ND = 12

POWERPLAY_BONUS_RUNS = 2   # bonus added to 4/5/6 when powerplay active
POWERPLAY_ELIGIBLE_RUNS = {4, 5, 6}

WIDE_RUN_VALUE = 1

# --- Storage paths ---
DATA_DIR = os.getenv("DATA_DIR", "data")
MEDIA_ASSETS_FILE = os.path.join(DATA_DIR, "media_assets.json")
PLAYER_STATS_FILE = os.path.join(DATA_DIR, "player_stats.json")

EVENT_KEYS = ["FOUR", "SIX", "DOT", "OUT", "FREE_HIT", "WIDE", "WIN"]

EVENT_KEY_DESCRIPTIONS = {
    "FOUR": "Fires when a batter scores a 4 (off the bat, not counting powerplay bonus).",
    "SIX": "Fires when a batter scores a 6.",
    "DOT": "Fires when a batter scores a dot ball (0 runs, no wicket).",
    "OUT": "Fires the instant a batter is dismissed (bowler number == batter number).",
    "FREE_HIT": "Fires when a Free Hit delivery is awarded (after a qualifying lock).",
    "WIDE": "Fires whenever the bowler bowls a Wide (W).",
    "WIN": "Fires the instant a match/tournament result is finalized (win/draw/walkover).",
}
