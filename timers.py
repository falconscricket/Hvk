from telegram.ext import ContextTypes
from gamestate import get_match, remove_match, GamePhase, GameMode
from utils import user_mention, build_batting_keyboard
from notify import notify_event, notify_bowler_turn, notify_batter_turn
from scoreboard import render_scoreboard

async def turn_timer_callback(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id = job.data["chat_id"]
    step = job.data["step"]
    match = get_match(chat_id)
    
    if not match or match.phase in [GamePhase.LOBBY, GamePhase.ENDED]:
        return

    async with match.lock:
        active_player = match.current_batter if match.pending_bowl_delivery is not None else match.current_bowler
        if not active_player:
            return

        if step == 30:
            await notify_event(context.bot, chat_id, f"⏰ 30s Reminder: {user_mention(active_player.user_id, active_player.name)}, please take your turn!")
        elif step == 50:
            await notify_event(context.bot, chat_id, f"⚠️ 10 Seconds Left! {user_mention(active_player.user_id, active_player.name)} move fast!")
        elif step == 60:
            # 60s Foul Handling
            active_player.foul_count += 1
            if active_player.foul_count == 1:
                # Penalty 1
                if match.mode == GameMode.TEAM_MATCH:
                    penalty_text = "Opponent team awarded +6 runs."
                else:
                    active_player.runs_scored = max(0, active_player.runs_scored - 6)
                    penalty_text = "-6 runs penalty applied."
                    
                await notify_event(
                    context.bot, chat_id,
                    f"⌛ <b>Foul #1 for {user_mention(active_player.user_id, active_player.name)}!</b> {penalty_text} Same player will retry this turn."
                )
                # Re-trigger turn prompt
                if match.pending_bowl_delivery is None:
                    await notify_bowler_turn(context.bot, chat_id, active_player.user_id, active_player.name)
                else:
                    await notify_batter_turn(context.bot, chat_id, active_player.user_id, active_player.name, build_batting_keyboard())

            elif active_player.foul_count >= 2:
                # Penalty 2: Removal
                await notify_event(
                    context.bot, chat_id,
                    f"🚫 {user_mention(active_player.user_id, active_player.name)} <b>fouled twice and has been removed from the match.</b>"
                )
                if match.mode == GameMode.ONE_VS_ONE:
                    match.phase = GamePhase.ENDED
                    await notify_event(context.bot, chat_id, "🏆 Match ended due to player removal penalty!\n\n" + render_scoreboard(match))
                    remove_match(chat_id)

async def autostart_lobby_callback(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.data["chat_id"]
    match = get_match(chat_id)
    if not match or match.phase != GamePhase.LOBBY:
        return

    async with match.lock:
        if len(match.solo_players) >= 4:
            match.phase = GamePhase.OVER_SELECTION
            await notify_event(context.bot, chat_id, "⏰ 2 Minutes elapsed! Tournament auto-starting with registered players.")
        else:
            await notify_event(context.bot, chat_id, "❌ Tournament cancelled: Minimum 4 players required were not met in 2 minutes.")
            remove_match(chat_id)
