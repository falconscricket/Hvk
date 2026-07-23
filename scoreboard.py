"""
scoreboard.py — Real-time formatted scoreboard renderer.
"""
from __future__ import annotations

from gamestate import Match
from utils import mention_html


def render_scoreboard(match: Match) -> str:
    inn = match.current_innings
    lines = ["🏏 <b>SCOREBOARD</b>"]

    batter_id = match.current_batter_id()
    bowler_id = match.current_bowler_id()

    lines.append(f"Innings {match.innings_no} — <b>{inn.total_runs}</b> runs off {inn.legal_balls} legal ball(s)")
    if inn.target is not None:
        remaining = max(inn.target - inn.total_runs, 0)
        lines.append(f"🎯 Target: <b>{inn.target}</b>  (need {remaining} more)")

    if batter_id and batter_id in match.players:
        p = match.players[batter_id]
        lines.append(f"🏏 On strike: {mention_html(p.user_id, p.first_name)} "
                      f"({p.runs} off {p.balls_faced}, SR {p.strike_rate})")
    if bowler_id and bowler_id in match.players:
        b = match.players[bowler_id]
        lines.append(f"🎯 Bowling: {mention_html(b.user_id, b.first_name)} ({b.wickets_taken} wkt)")

    if match.powerplay_active:
        lines.append("⚡ Powerplay is ACTIVE (+2 on 4/5/6)")

    if inn.free_hit_next:
        lines.append("🆓 Next ball is a FREE HIT")

    # Orange Cap / Purple Cap across current players
    if match.players:
        top_run_scorer = max(match.players.values(), key=lambda p: p.runs, default=None)
        top_wicket_taker = max(match.players.values(), key=lambda p: p.wickets_taken, default=None)
        if top_run_scorer and top_run_scorer.runs > 0:
            lines.append(f"🟠 Orange Cap: {mention_html(top_run_scorer.user_id, top_run_scorer.first_name)} "
                         f"({top_run_scorer.runs})")
        if top_wicket_taker and top_wicket_taker.wickets_taken > 0:
            lines.append(f"🟣 Purple Cap: {mention_html(top_wicket_taker.user_id, top_wicket_taker.first_name)} "
                         f"({top_wicket_taker.wickets_taken})")

    if inn.ball_log:
        recent = inn.ball_log[-6:]
        symbols = []
        for ev in recent:
            if ev.is_wicket:
                symbols.append("W")
            elif ev.is_wide:
                symbols.append("wd")
            else:
                symbols.append(str(ev.runs_scored))
        lines.append("Recent balls: " + " | ".join(symbols))

    return "\n".join(lines)


def render_result(match: Match) -> str:
    lines = ["🏆 <b>MATCH RESULT</b>"]
    if match.result_text:
        lines.append(match.result_text)
    if match.winner_id and match.winner_id in match.players:
        w = match.players[match.winner_id]
        lines.append(f"🎉 Winner: {mention_html(w.user_id, w.first_name)}")
    return "\n".join(lines)
