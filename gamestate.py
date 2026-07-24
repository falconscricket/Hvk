import asyncio
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Set

class GameMode(Enum):
    ONE_VS_ONE = auto()
    SOLO_TOURNAMENT = auto()
    TEAM_MATCH = auto()

class GamePhase(Enum):
    LOBBY = auto()
    OVER_SELECTION = auto()
    TOSS = auto()
    INNINGS_1 = auto()
    INNINGS_2 = auto()
    ENDED = auto()

class Team(Enum):
    A = "Team A"
    B = "Team B"

@dataclass
class Player:
    user_id: int
    name: str
    username: Optional[str] = None
    runs_scored: int = 0
    balls_faced: int = 0
    fours: int = 0
    sixes: int = 0
    wickets_taken: int = 0
    overs_bowled_balls: int = 0
    runs_conceded: int = 0
    is_out: bool = False
    foul_count: int = 0
    ball_log: List[str] = field(default_factory=list)

@dataclass
class AuctionState:
    auction_id: str
    host_id: int
    captains: Dict[int, str] = field(default_factory=dict)  # user_id -> team_name
    purses: Dict[int, float] = field(default_factory=dict)
    current_bid_player: Optional[str] = None
    highest_bidder: Optional[int] = None
    highest_bid: float = 0.0
    unsold_pool: List[str] = field(default_factory=list)
    is_paused: bool = False

@dataclass
class MatchState:
    chat_id: int
    mode: GameMode
    phase: GamePhase = GamePhase.LOBBY
    host_id: Optional[int] = None
    creator_id: Optional[int] = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    
    # Teams & Players
    team_a: List[Player] = field(default_factory=list)
    team_b: List[Player] = field(default_factory=list)
    solo_players: List[Player] = field(default_factory=list)
    
    # Active Positions
    current_batter: Optional[Player] = None
    current_bowler: Optional[Player] = None
    batter_index: int = 0
    bowler_index: int = 0
    
    # Dynamic Game Settings
    powerplay_active: bool = False
    balls_per_over_setting: int = 6
    total_overs_setting: int = 2
    
    # Game Mechanics State
    current_innings: int = 1
    target_runs: Optional[int] = None
    innings_1_runs: int = 0
    total_wickets_team_a: int = 0
    total_wickets_team_b: int = 0
    legal_balls_in_over: int = 0
    current_over_number: int = 0
    
    # Delivery Engine Locks & Pending Values
    pending_bowl_delivery: Optional[str] = None  # "0"-"6" or "W"
    is_free_hit: bool = False
    recent_bowler_wickets_consecutive: int = 0  # For hat-trick tracking
    
    # Captain Approval Flow
    host_proposal_new_id: Optional[int] = None
    host_proposal_approvals: Set[int] = field(default_factory=set)

# Global memory-resident active game registry
ACTIVE_MATCHES: Dict[int, MatchState] = {}
AUCTIONS: Dict[int, AuctionState] = {}

def get_match(chat_id: int) -> Optional[MatchState]:
    return ACTIVE_MATCHES.get(chat_id)

def create_match(chat_id: int, mode: GameMode, creator_id: int) -> MatchState:
    match = MatchState(chat_id=chat_id, mode=mode, creator_id=creator_id)
    ACTIVE_MATCHES[chat_id] = match
    return match

def remove_match(chat_id: int):
    ACTIVE_MATCHES.pop(chat_id, None)
