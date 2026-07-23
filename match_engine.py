"""
match_engine.py — Delivery evaluation, runs, wickets, strike/bowler rotation,
target calculation, win/draw checks, batting-order advancement.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from config import POWERPLAY_BONUS_RUNS, POWERPLAY_ELIGIBLE_RUNS, WIDE_RUN_VALUE
from gamestate import BallEvent, InningsState, Match, Player


@dataclass
class DeliveryResult:
    event: BallEvent
    runs_added: int
    wicket: bool
    wide: bool
    free_hit_awarded_next: bool
    match_ended: bool = False
    result_text: Optional[str] = None
    winner_id: Optional[int] = None
    innings_ended: bool = False


def _detect_free_hit_lock(inn: InningsState, new_number: str) -> bool:
    """
    House rule: if the bowler's current and immediately-previous legal delivery
    form the pair {1, 6} (in either order), the NEXT ball is a Free Hit.
    """
    if new_number == "W":
        return False
    history = inn.last_bowler_numbers
    if not history:
        return False
    prev = history[-1]
    pair = {prev, new_number}
    return pair == {"1", "6"}


def resolve_delivery(
    match: Match,
    bowler: Player,
    batter: Player,
    bowler_input: str,
    batter_input: Optional[str] = None,
) -> DeliveryResult:
    """
    Evaluate one completed delivery (bowler number/W + batter number already collected).
    Mutates match/innings/player state in place and returns a summary.
    """
    inn = match.current_innings
    is_wide = bowler_input == "W"
    free_hit_this_ball = inn.free_hit_next
    inn.free_hit_next = False

    event = BallEvent(
        bowler_id=bowler.user_id,
        batter_id=batter.user_id,
        bowler_input=bowler_input,
        batter_input=batter_input,
        is_wide=is_wide,
        is_free_hit=free_hit_this_ball,
    )

    result = DeliveryResult(event=event, runs_added=0, wicket=False, wide=is_wide,
                            free_hit_awarded_next=False)

    if is_wide:
        inn.total_runs += WIDE_RUN_VALUE
        event.runs_scored = WIDE_RUN_VALUE
        result.runs_added = WIDE_RUN_VALUE
        # Wides do not increment legal ball count and do not consume the batter's turn.
        _maybe_check_target(match, inn, result)
        return result

    # Legal delivery.
    inn.legal_balls += 1
    inn.balls_this_spell += 1
    batter.balls_faced += 1

    is_wicket = (bowler_input == batter_input) and not free_hit_this_ball

    if is_wicket:
        event.is_wicket = True
        result.wicket = True
        batter.is_out = True
        bowler.wickets_taken += 1
        inn.consecutive_wickets_same_bowler += 1
    else:
        runs = int(batter_input)
        if match.powerplay_active and runs in POWERPLAY_ELIGIBLE_RUNS:
            runs += POWERPLAY_BONUS_RUNS
        batter.runs += runs
        inn.total_runs += runs
        event.runs_scored = runs
        result.runs_added = runs
        inn.consecutive_wickets_same_bowler = 0

    # Free-hit "lock" detection based on this bowler's number sequence.
    if _detect_free_hit_lock(inn, bowler_input):
        inn.free_hit_next = True
        result.free_hit_awarded_next = True

    inn.last_bowler_numbers.append(bowler_input)
    inn.ball_log.append(event)

    _maybe_check_target(match, inn, result)
    return result


def _maybe_check_target(match: Match, inn: InningsState, result: DeliveryResult) -> None:
    """Innings-2 only: check instant win/draw the moment target math resolves."""
    if match.innings_no != 2 or inn.target is None:
        return
    if inn.total_runs >= inn.target:
        result.match_ended = True
        result.innings_ended = True
        result.result_text = "batter_win"
        # winner_id filled in by caller (needs current batter identity at call site)


def check_bowler_rotation_due(inn: InningsState) -> bool:
    """True once the current bowler has completed their spell (over_length legal balls)."""
    return inn.balls_this_spell >= inn.over_length


def advance_bowler(inn: InningsState) -> None:
    inn.current_bowler_idx += 1
    inn.balls_this_spell = 0
    inn.last_bowler_numbers = []


def advance_batter_after_wicket(inn: InningsState) -> None:
    inn.current_batter_idx += 1


def start_innings_2(match: Match, target_runs: int) -> None:
    match.innings_no = 2
    match.innings2.target = target_runs + 1
    match.phase_note = "innings2"


def hat_trick_zero_forbidden(inn: InningsState) -> bool:
    """Batter cannot enter 0 immediately following back-to-back wickets by the same bowler."""
    return inn.consecutive_wickets_same_bowler >= 2
