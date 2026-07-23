"""
gamestate.py — Enums and dataclasses describing an in-progress match.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


class GameMode(Enum):
    ONE_V_ONE = auto()
    SOLO_TOURNAMENT = auto()
    TEAM_MATCH = auto()


class GamePhase(Enum):
    LOBBY = auto()
    TOSS = auto()
    INNINGS_1 = auto()
    INNINGS_2 = auto()
    COMPLETE = auto()


class Team(Enum):
    A = "A"
    B = "B"
    NONE = None


@dataclass
class Player:
    user_id: int
    first_name: str
    username: Optional[str] = None
    team: Team = Team.NONE
    roster_no: Optional[int] = None
    runs: int = 0
    balls_faced: int = 0
    wickets_taken: int = 0
    fouls: int = 0                 # foul count *within the current match*
    eligible: bool = True          # False once removed (2nd foul / /leave)
    is_out: bool = False           # dismissed for the current innings

    @property
    def strike_rate(self) -> float:
        if self.balls_faced == 0:
            return 0.0
        return round(self.runs / self.balls_faced * 100, 2)


@dataclass
class BallEvent:
    bowler_id: int
    batter_id: int
    bowler_input: str      # "1".."6" or "W"
    batter_input: Optional[str]  # "0".."6", None if not yet resolved
    runs_scored: int = 0
    is_wicket: bool = False
    is_wide: bool = False
    is_free_hit: bool = False
    timestamp: float = field(default_factory=time.time)


@dataclass
class InningsState:
    batting_order: list[int] = field(default_factory=list)   # user_ids, in order
    bowling_order: list[int] = field(default_factory=list)
    current_batter_idx: int = 0
    current_bowler_idx: int = 0
    total_runs: int = 0
    legal_balls: int = 0
    target: Optional[int] = None
    over_length: int = 6           # legal balls per bowling spell (solo tournament: 1 or 3)
    balls_this_spell: int = 0
    last_bowler_numbers: list[str] = field(default_factory=list)  # for free-hit "lock" detection
    consecutive_wickets_same_bowler: int = 0
    free_hit_next: bool = False
    ball_log: list[BallEvent] = field(default_factory=list)
    pending_bowler_input: Optional[str] = None


@dataclass
class Match:
    chat_id: int
    mode: GameMode
    phase: GamePhase = GamePhase.LOBBY
    created_by: int = 0
    created_at: float = field(default_factory=time.time)
    players: dict[int, Player] = field(default_factory=dict)   # user_id -> Player
    innings_no: int = 1
    innings1: InningsState = field(default_factory=InningsState)
    innings2: InningsState = field(default_factory=InningsState)
    powerplay_active: bool = False
    host_id: Optional[int] = None
    winner_id: Optional[int] = None
    result_text: Optional[str] = None

    @property
    def current_innings(self) -> InningsState:
        return self.innings1 if self.innings_no == 1 else self.innings2

    def eligible_players(self) -> list[Player]:
        return [p for p in self.players.values() if p.eligible]

    def current_bowler_id(self) -> Optional[int]:
        inn = self.current_innings
        order = [uid for uid in inn.bowling_order if self.players[uid].eligible]
        if not order:
            return None
        idx = inn.current_bowler_idx % len(order)
        return order[idx]

    def current_batter_id(self) -> Optional[int]:
        inn = self.current_innings
        order = [uid for uid in inn.batting_order
                 if self.players[uid].eligible and not self.players[uid].is_out]
        if not order:
            return None
        idx = inn.current_batter_idx % len(order)
        return order[idx]
