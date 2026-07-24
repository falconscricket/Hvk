import html
from gamestate import MatchState, Player

def render_player_row(p: Player) -> str:
    ov_str = f"{p.overs_bowled_balls // 6}.{p.overs_bowled_balls % 6}-{p.runs_conceded}"
    log = "•".join(p.ball_log[-6:]) if p.ball_log else "None"
    return (
        f"| {p.name[:16]:<16} | {f'{p.runs_scored}({p.balls_faced})':<4} | {p.fours:<2} | {p.sixes:<2} | {p.wickets_taken:<1} | {ov_str:<6} |\n"
        f"| ╰⊚ ID: {p.user_id:<11} |      |    |    |   |        |\n"
        f"| ╰⊚({log:<10}) |      |    |    |   |        |\n"
        f"+------------------+------+----+----+---+--------+"
    )

def render_scoreboard(match: MatchState) -> str:
    host_str = f"User-{match.host_id}" if match.host_id else "None"
    
    # Team A Table
    team_a_rows = "\n".join([render_player_row(p) for p in match.team_a]) if match.team_a else "| No Players         | 0(0) | 0  | 0  | 0 | 0.0-0  |\n+------------------+------+----+----+---+--------+"
    team_a_runs = sum(p.runs_scored for p in match.team_a)
    
    # Team B Table
    team_b_rows = "\n".join([render_player_row(p) for p in match.team_b]) if match.team_b else "| No Players         | 0(0) | 0  | 0  | 0 | 0.0-0  |\n+------------------+------+----+----+---+--------+"
    team_b_runs = sum(p.runs_scored for p in match.team_b)
    
    all_players = match.team_a + match.team_b + match.solo_players
    player_id_list = "\n".join([f"• {html.escape(p.name)}: <code>{p.user_id}</code>" for p in all_players])

    return f"""<pre>
📊 Game #{match.chat_id} Scoreboard

╭━─━─━─━─≪✠≫─━─━─━─━╮

───────⊱ Tᴇᴀᴍ - A ⊰──────

+------------------+------+----+----+---+--------+
| Name             | R(B) | 4s | 6s | W | O-R    |
+------------------+------+----+----+---+--------+
{team_a_rows}

╭──────── • ◆ • ─────────
ᴛᴇᴀᴍ A sᴄᴏʀᴇ = {team_a_runs}/{match.total_wickets_team_a} ʀᴜɴs
╰──────── • ◆ • ─────────

× •-•-•-•-•-••-•-•⟮ 🏏 ⟯•-•-•-•-•-•-•-•-• ×

───────⊱ Tᴇᴀᴍ - B ⊰──────

+------------------+------+----+----+---+--------+
| Name             | R(B) | 4s | 6s | W | O-R    |
+------------------+------+----+----+---+--------+
{team_b_rows}

╭──────── • ◆ • ─────────
ᴛᴇᴀᴍ ʙ sᴄᴏʀᴇ = {team_b_runs}/{match.total_wickets_team_b} ʀᴜɴs
╰──────── • ◆ • ─────────

༺═────────────────═༻
</pre>

👑<b>Host:</b> {host_str}

🔑 <b>Player IDs:</b>
{player_id_list}
"""
