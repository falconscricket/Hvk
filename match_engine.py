from gamestate import MatchState, Player, GamePhase, GameMode
from utils import user_mention
from notify import notify_event
from scoreboard import render_scoreboard

async def evaluate_delivery(bot, match: MatchState, bat_input: int) -> dict:
    async with match.lock:
        bowl_str = match.pending_bowl_delivery
        match.pending_bowl_delivery = None  # Reset PM lock
        
        batter = match.current_batter
        bowler = match.current_bowler
        
        result = {
            "is_out": False,
            "is_wide": False,
            "runs": 0,
            "media": None,
            "text": "",
            "match_ended": False
        }
        
        if not batter or not bowler:
            return result

        # Handle Wide Ball
        if bowl_str == "W":
            result["is_wide"] = True
            result["runs"] = 1
            result["media"] = "WIDE"
            if match.current_innings == 1:
                match.innings_1_runs += 1
            batter.runs_scored += 0 # Extras don't add to batsman
            bowler.runs_conceded += 1
            bowler.ball_log.append("W")
            result["text"] = f"🚨 <b>WIDE BALL!</b> +1 Extra Run. {user_mention(bowler.user_id, bowler.name)} bowls again."
            return result

        bowl_input = int(bowl_str)
        batter.balls_faced += 1
        bowler.overs_bowled_balls += 1

        # Check Out vs Runs
        if bat_input == bowl_input:
            if match.is_free_hit:
                match.is_free_hit = False
                result["media"] = "DOT"
                result["text"] = f"🛡️ <b>FREE HIT SURVIVED!</b> {user_mention(batter.user_id, batter.name)} matched numbers but is NOT OUT!"
                bowler.ball_log.append("0")
            else:
                result["is_out"] = True
                batter.is_out = True
                bowler.wickets_taken += 1
                bowler.recent_bowler_wickets_consecutive += 1
                match.recent_bowler_wickets_consecutive = bowler.recent_bowler_wickets_consecutive
                
                if match.current_innings == 1:
                    match.total_wickets_team_a += 1
                else:
                    match.total_wickets_team_b += 1
                    
                bowler.ball_log.append("W")
                result["media"] = "OUT"
                result["text"] = f"☝️ <b>OUT!</b> {user_mention(batter.user_id, batter.name)} enters {bat_input} and is walking back to the pavilion!"
        else:
            bowler.recent_bowler_wickets_consecutive = 0
            match.recent_bowler_wickets_consecutive = 0
            runs = bat_input
            
            # Powerplay impact
            if match.powerplay_active and runs in [4, 5, 6]:
                runs += 2
                result["text"] += "🔥 <b>POWERPLAY IMPACT! +2 Bonus Runs!</b>\n"
                
            if bat_input == 4:
                batter.fours += 1
                result["media"] = "FOUR"
            elif bat_input == 6:
                batter.sixes += 1
                result["media"] = "SIX"
            elif bat_input == 0:
                result["media"] = "DOT"

            # Check Free Hit Lock sequence (1-6 or 6-1)
            if (bat_input == 1 and bowl_input == 6) or (bat_input == 6 and bowl_input == 1):
                match.is_free_hit = True
                result["media"] = "FREE_HIT"
                result["text"] += "⚡ <b>FREE HIT TRIGGERED!</b> Next delivery is a Free Hit!\n"

            batter.runs_scored += runs
            bowler.runs_conceded += runs
            bowler.ball_log.append(str(runs))
            
            if match.current_innings == 1:
                match.innings_1_runs += runs
            
            result["runs"] = runs
            result["text"] += f"🏏 {user_mention(batter.user_id, batter.name)} scores <b>{runs}</b> runs!"

        if not result["is_wide"]:
            match.legal_balls_in_over += 1

        # Innings 2 Target Check
        if match.current_innings == 2 and match.target_runs is not None:
            team_b_score = sum(p.runs_scored for p in match.team_b) if match.mode == GameMode.TEAM_MATCH else batter.runs_scored
            if team_b_score >= match.target_runs:
                result["match_ended"] = True
                match.phase = GamePhase.ENDED
                result["media"] = "WIN"
                result["text"] += f"\n\n🏆 <b>TARGET REACHED!</b> {user_mention(batter.user_id, batter.name)} wins the game!"

        return result
        
