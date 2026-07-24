import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
BOT_USERNAME: str = os.getenv("BOT_USERNAME", "HandCricketRobot")
DATABASE_PATH: str = os.getenv("DATABASE_PATH", "data/handcricket.db")
MEDIA_ASSETS_PATH: str = os.getenv("MEDIA_ASSETS_PATH", "media_assets.json")

# Dual Owners support
raw_owners = os.getenv("OWNER_IDS", "")
OWNER_IDS: list[int] = [int(x.strip()) for x in raw_owners.split(",") if x.strip().isdigit()]

# Default Game Constants
DEFAULT_INNINGS_OVERS = 2
BALLS_PER_OVER = 6
FOUL_TIMEOUT_SECONDS = 60
REMINDER_30S_SECONDS = 30
ALERT_50S_SECONDS = 50
HOST_INACTIVITY_TIMEOUT_SECONDS = 300  # 5 minutes
LOBBY_AUTOSTART_SECONDS = 120  # 2 minutes
MIN_TOURNAMENT_PLAYERS = 4
MAX_TOURNAMENT_PLAYERS = 30
