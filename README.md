# Hand Cricket Telegram Bot

Built against `hand-cricket-bot-spec-v5.md`. This delivery implements the
**core engine** plus **1v1 Normal Match** and **Solo Tournament (4-30
players)** end-to-end, including every v4/v5 amendment:

- ✅ Bidirectional nav buttons on every single turn handoff (v4 Rule 1)
- ✅ PM routing works no matter when the bowler opened the bot's PM (v4 Rule 2)
- ✅ Mandatory foul re-notification the next time a fouled player's turn
  cycles back around (v4 Rule 3)
- ✅ PM delivery-lock text is `"✅ Already Bowled"` (v5 Rule 1)
- ✅ Solo Tournament lobby reminders at the 1-minute and 30-second marks (v5 Rule 2)
- ✅ Text-only delivery input (bowler `1-6`/`W` in PM, batter `0-6` in group), no digit buttons
- ✅ Bowler can never enter `0`
- ✅ 60s turn timer (30s / 50s / 60s foul), 1st foul -6, 2nd foul -12 + removal
- ✅ Powerplay (`/pp`), Wide (+1, re-ball), Free Hit lock detection, hat-trick `0` restriction
- ✅ Player-Count Integrity (wickets never end a match on their own)
- ✅ Owner panel (`/setmedia`, `/listmedia`, `/restart`) with dual Owner IDs and Owner Override
- ✅ `send_event_media()` actually wired into FOUR/SIX/DOT/OUT/FREE_HIT/WIDE/WIN
- ✅ `/leave`, `/score`, `/end`, `/Feedback`
- ✅ `asyncio.Lock()` per `chat_id` around every delivery resolution

## Not included in this delivery

Your spec's own status table already marks these "Not yet implemented" —
they're each a substantial separate build:

- **Team Match ("Host Match") ball-by-ball delivery engine.** `/batting` and
  `/bowling` currently just reply that they're unavailable; there's no
  11-a-side roster/host-approval delivery loop wired up yet.
- **Auction subsystem** (`auction.py`, all `/add_cap` … `/rm_auction_id`
  commands) — captains, purses, live bidding, unsold pool.
- **`/swap`** and **`/host_change`** for Host Match.

All of the commands above are still *registered* (per the spec's mandatory
command list) — they just reply honestly that they're not wired up yet,
instead of silently failing as "unknown command."

## Setup

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# edit .env: BOT_TOKEN, BOT_USERNAME, OWNER_ID_1, OWNER_ID_2
python bot.py
```

## Project layout

```
config.py           Configuration constants (env-driven)
gamestate.py         Enums + dataclasses (GameMode, GamePhase, Player, Match, ...)
match_engine.py       Delivery evaluation, runs/wickets, free hit, targets
scoreboard.py         Scoreboard + result rendering
timers.py             JobQueue turn timer + foul engine + tournament lobby timer
media.py              media_assets.json store + send_event_media()
owner.py              /setmedia /listmedia /restart
notify.py             Central notification dispatcher + active-bowler PM registry
utils.py              Mentions, input sanitizers, nav-only keyboards
database.py           Player career stats JSON store
bot.py               Application entry point, handler registration
handlers/
  common.py           Shared delivery flow (PM bowler input, group batter input)
  onevone.py           1v1 mode
  solo.py              Solo Tournament mode
  leave.py             Cross-mode /leave dispatcher
  misc.py              /start /score /end /pp /Feedback + honest stubs
```

## A few implementation notes / assumptions

- **Free Hit "lock" rule:** the spec's example (`1-6` or `6-1`) was read as:
  if a bowler's current and immediately-previous legal delivery form the pair
  `{1, 6}` in either order, the *next* ball is a Free Hit. Adjust
  `_detect_free_hit_lock()` in `match_engine.py` if you meant something else.
- **PM -> Group button:** Telegram doesn't allow bots to deep-link into an
  arbitrary private group chat. The button uses a `t.me/c/...` message link
  when the chat is a supergroup (works for members), and falls back to the
  bot's own PM link otherwise — a normal Telegram platform constraint, not a
  bug in the spec's rule.
