import os
import sqlite3
import aiosqlite
import json
from config import DATABASE_PATH, MEDIA_ASSETS_PATH

class DatabaseManager:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS player_stats (
                    user_id INTEGER PRIMARY KEY,
                    matches INTEGER DEFAULT 0,
                    runs INTEGER DEFAULT 0,
                    wickets INTEGER DEFAULT 0,
                    fours INTEGER DEFAULT 0,
                    sixes INTEGER DEFAULT 0
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS auction_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    auction_id TEXT,
                    player_name TEXT,
                    sold_to TEXT,
                    amount REAL
                )
            """)
            await db.commit()

    async def update_stats(self, user_id: int, runs: int, wickets: int, fours: int, sixes: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO player_stats (user_id, matches, runs, wickets, fours, sixes)
                VALUES (?, 1, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    matches = matches + 1,
                    runs = runs + excluded.runs,
                    wickets = wickets + excluded.wickets,
                    fours = fours + excluded.fours,
                    sixes = sixes + excluded.sixes
            """, (user_id, runs, wickets, fours, sixes))
            await db.commit()

db_manager = DatabaseManager()
