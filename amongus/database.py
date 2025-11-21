"""SQLite3 database handler for Among Us bot"""
import sqlite3
import json
import asyncio
from typing import Optional, Dict, List, Any
from datetime import datetime
import aiosqlite

class GameDatabase:
    """Async SQLite database for game state and player stats"""
    
    def __init__(self, db_path: str = "amongus.db"):
        self.db_path = db_path
        self.connection: Optional[aiosqlite.Connection] = None
    
    async def initialize(self):
        """Initialize database connection and create tables"""
        self.connection = await aiosqlite.connect(self.db_path)
        self.connection.row_factory = aiosqlite.Row
        await self._create_tables()
        await self._clear_temporary_tables()
        print("✅ Database initialized successfully")
    
    async def close(self):
        """Close database connection"""
        if self.connection:
            await self.connection.close()
            print("Database connection closed")
    
    async def _create_tables(self):
        """Create all database tables"""
        if self.connection is None:
            raise ValueError("Database connection not initialized. Call initialize() first.")
        await self.connection.executescript("""
            -- PERSISTENT TABLES (Keep on startup)
            
            CREATE TABLE IF NOT EXISTS player_stats (
                user_id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                total_games INTEGER DEFAULT 0,
                games_won INTEGER DEFAULT 0,
                games_lost INTEGER DEFAULT 0,
                impostor_wins INTEGER DEFAULT 0,
                crewmate_wins INTEGER DEFAULT 0,
                scientist_wins INTEGER DEFAULT 0,
                engineer_wins INTEGER DEFAULT 0,
                tasks_completed INTEGER DEFAULT 0,
                kills_made INTEGER DEFAULT 0,
                times_killed INTEGER DEFAULT 0,
                emergency_meetings_called INTEGER DEFAULT 0,
                correct_votes INTEGER DEFAULT 0,
                total_votes INTEGER DEFAULT 0,
                last_played TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS player_preferences (
                user_id INTEGER PRIMARY KEY,
                preferred_color TEXT,
                notifications_enabled INTEGER DEFAULT 1,
                stats_public INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES player_stats(user_id)
            );
            
            -- TEMPORARY TABLES (Clear on startup)
            
            DROP TABLE IF EXISTS games;
            CREATE TABLE IF NOT EXISTS games (
                channel_id INTEGER PRIMARY KEY,
                guild_id INTEGER NOT NULL,
                game_code TEXT NOT NULL,
                phase TEXT DEFAULT 'lobby',
                max_players INTEGER DEFAULT 10,
                min_players INTEGER DEFAULT 4,
                impostor_count INTEGER DEFAULT 1,
                scientist_count INTEGER DEFAULT 0,
                engineer_count INTEGER DEFAULT 0,
                guardian_angel_count INTEGER DEFAULT 0,
                active_sabotage TEXT,
                kill_cooldown INTEGER DEFAULT 18,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            
            DROP TABLE IF EXISTS game_players;
            CREATE TABLE IF NOT EXISTS game_players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                avatar_url TEXT,
                is_bot INTEGER DEFAULT 0,
                alive INTEGER DEFAULT 1,
                role TEXT DEFAULT 'Crewmate',
                role_type TEXT DEFAULT 'Crewmate',
                color TEXT,
                location TEXT DEFAULT 'Cafeteria',
                voted_for INTEGER,
                kill_cooldown INTEGER DEFAULT 0,
                sabotage_cooldown INTEGER DEFAULT 0,
                emergency_meetings_left INTEGER DEFAULT 1,
                in_vent INTEGER DEFAULT 0,
                can_vent INTEGER DEFAULT 0,
                task_speed_multiplier REAL DEFAULT 1.0,
                sabotage_fix_speed REAL DEFAULT 1.0,
                shielded INTEGER DEFAULT 0,
                shielded_by INTEGER,
                shield_cooldown INTEGER DEFAULT 0,
                shields_remaining INTEGER DEFAULT 2,
                FOREIGN KEY (channel_id) REFERENCES games(channel_id) ON DELETE CASCADE,
                UNIQUE(channel_id, user_id)
            );
            
            CREATE TABLE IF NOT EXISTS game_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_player_id INTEGER NOT NULL,
                task_type TEXT NOT NULL,
                location TEXT NOT NULL,
                completed INTEGER DEFAULT 0,
                FOREIGN KEY (game_player_id) REFERENCES game_players(id) ON DELETE CASCADE
            );
            
            CREATE TABLE IF NOT EXISTS game_votes (
                channel_id INTEGER NOT NULL,
                voter_id INTEGER NOT NULL,
                target_id INTEGER NOT NULL,
                PRIMARY KEY (channel_id, voter_id),
                FOREIGN KEY (channel_id) REFERENCES games(channel_id) ON DELETE CASCADE
            );
            
            CREATE TABLE IF NOT EXISTS game_impostors (
                channel_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                PRIMARY KEY (channel_id, user_id),
                FOREIGN KEY (channel_id) REFERENCES games(channel_id) ON DELETE CASCADE
            );
            
            -- Create indexes for better performance
            CREATE INDEX IF NOT EXISTS idx_game_players_channel ON game_players(channel_id);
            CREATE INDEX IF NOT EXISTS idx_game_players_user ON game_players(user_id);
            CREATE INDEX IF NOT EXISTS idx_game_tasks_player ON game_tasks(game_player_id);
        """)
        await self.connection.commit()
    
    async def _clear_temporary_tables(self):
        """Clear all temporary game data on startup"""
        if self.connection is None:
            raise ValueError("Database connection not initialized. Call initialize() first.")
        await self.connection.executescript("""
            DELETE FROM game_votes;
            DELETE FROM game_impostors;
            DELETE FROM game_tasks;
            DELETE FROM game_players;
            DELETE FROM games;
        """)
        await self.connection.commit()
        print("🧹 Temporary game data cleared")
 
    async def create_game(self, channel_id: int, guild_id: int, game_code: str, max_players: int = 10, impostor_count: int = 1, scientist_count: int = 0, engineer_count: int = 0, guardian_angel_count: int = 0):
        if self.connection is None:
            raise ValueError("Database connection not initialized. Call initialize() first.")
        await self.connection.execute("""
            INSERT INTO games (channel_id, guild_id, game_code, max_players, impostor_count, scientist_count, engineer_count, guardian_angel_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (channel_id, guild_id, game_code, max_players, impostor_count, scientist_count, engineer_count, guardian_angel_count))
        await self.connection.commit()
    
    async def get_game(self, channel_id: int) -> Optional[Dict[str, Any]]:
        """Get game data"""
        if self.connection is None:
            raise ValueError("Database connection not initialized. Call initialize() first.")
        async with self.connection.execute("""
            SELECT * FROM games WHERE channel_id = ?
        """, (channel_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None
    
    async def update_game(self, channel_id: int, **kwargs):
        """Update game fields"""
        if self.connection is None:
            raise ValueError("Database connection not initialized. Call initialize() first.")
        if not kwargs:
            return
        
        fields = ", ".join(f"{key} = ?" for key in kwargs.keys())
        values = list(kwargs.values()) + [channel_id]
        
        await self.connection.execute(f"""
            UPDATE games SET {fields} WHERE channel_id = ?
        """, values)
        await self.connection.commit()
    
    async def delete_game(self, channel_id: int):
        """Delete a game (cascades to all related data)"""
        if self.connection is None:
            raise ValueError("Database connection not initialized. Call initialize() first.")
        await self.connection.execute("DELETE FROM games WHERE channel_id = ?", (channel_id,))
        await self.connection.commit()
    
    async def game_exists(self, channel_id: int) -> bool:
        """Check if game exists"""
        if self.connection is None:
            raise ValueError("Database connection not initialized. Call initialize() first.")
        async with self.connection.execute("""
            SELECT 1 FROM games WHERE channel_id = ? LIMIT 1
        """, (channel_id,)) as cursor:
            return await cursor.fetchone() is not None
    
    async def get_game_by_code(self, game_code: str) -> Optional[Dict[str, Any]]:
        """Find game by game code"""
        if self.connection is None:
            raise ValueError("Database connection not initialized. Call initialize() first.")
        async with self.connection.execute("""
            SELECT * FROM games WHERE UPPER(game_code) = UPPER(?)
        """, (game_code,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def add_player(self, channel_id: int, user_id: int, name: str, avatar_url: str = "", 
                        is_bot: bool = False, color: str = "#FFFFFF"):
        """Add a player to a game"""
        if self.connection is None:
            raise ValueError("Database connection not initialized. Call initialize() first.")
        await self.connection.execute("""
            INSERT INTO game_players 
            (channel_id, user_id, name, avatar_url, is_bot, color)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (channel_id, user_id, name, avatar_url, int(is_bot), color))
        await self.connection.commit()
    
    async def get_players(self, channel_id: int) -> List[Dict[str, Any]]:
        """Get all players in a game"""
        if self.connection is None:
            raise ValueError("Database connection not initialized. Call initialize() first.")
        async with self.connection.execute("""
            SELECT * FROM game_players WHERE channel_id = ?
        """, (channel_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def get_player(self, channel_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific player"""
        if self.connection is None:
            raise ValueError("Database connection not initialized. Call initialize() first.")
        async with self.connection.execute("""
            SELECT * FROM game_players WHERE channel_id = ? AND user_id = ?
        """, (channel_id, user_id)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None
    
    async def update_player(self, channel_id: int, user_id: int, **kwargs):
        """Update player fields"""
        if self.connection is None:
            raise ValueError("Database connection not initialized. Call initialize() first.")
        if not kwargs:
            return
        
        fields = ", ".join(f"{key} = ?" for key in kwargs.keys())
        values = list(kwargs.values()) + [channel_id, user_id]
        
        await self.connection.execute(f"""
            UPDATE game_players SET {fields} WHERE channel_id = ? AND user_id = ?
        """, values)
        await self.connection.commit()
    
    async def remove_player(self, channel_id: int, user_id: int):
        """Remove a player from a game"""
        if self.connection is None:
            raise ValueError("Database connection not initialized. Call initialize() first.")
        await self.connection.execute("""
            DELETE FROM game_players WHERE channel_id = ? AND user_id = ?
        """, (channel_id, user_id))
        await self.connection.commit()
    
    async def get_player_count(self, channel_id: int) -> int:
        """Get number of players in a game"""
        if self.connection is None:
            raise ValueError("Database connection not initialized. Call initialize() first.")
        async with self.connection.execute("""
            SELECT COUNT(*) FROM game_players WHERE channel_id = ?
        """, (channel_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0
  
    async def add_task(self, game_player_id: int, task_type: str, location: str):
        """Add a task to a player"""
        if self.connection is None:
            raise ValueError("Database connection not initialized. Call initialize() first.")
        await self.connection.execute("""
            INSERT INTO game_tasks (game_player_id, task_type, location)
            VALUES (?, ?, ?)
        """, (game_player_id, task_type, location))
        await self.connection.commit()
    
    async def get_player_tasks(self, game_player_id: int) -> List[Dict[str, Any]]:
        """Get all tasks for a player"""
        if self.connection is None:
            raise ValueError("Database connection not initialized. Call initialize() first.")
        async with self.connection.execute("""
            SELECT * FROM game_tasks WHERE game_player_id = ?
        """, (game_player_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def update_task(self, task_id: int, completed: bool):
        """Mark a task as completed"""
        if self.connection is None:
            raise ValueError("Database connection not initialized. Call initialize() first.")
        await self.connection.execute("""
            UPDATE game_tasks SET completed = ? WHERE id = ?
        """, (int(completed), task_id))
        await self.connection.commit()
    
    async def get_task_progress(self, channel_id: int) -> tuple:
        """Get overall task completion for a game"""
        if self.connection is None:
            raise ValueError("Database connection not initialized. Call initialize() first.")
        async with self.connection.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) as completed
            FROM game_tasks gt
            JOIN game_players gp ON gt.game_player_id = gp.id
            WHERE gp.channel_id = ? AND gp.role IN ('Crewmate', 'Scientist', 'Engineer')
        """, (channel_id,)) as cursor:
            row = await cursor.fetchone()
            return (row['completed'] or 0, row['total'] or 0) if row else (0, 0)
           
    async def cast_vote(self, channel_id: int, voter_id: int, target_id: int):
        """Record a vote"""
        if self.connection is None:
            raise ValueError("Database connection not initialized. Call initialize() first.")
        await self.connection.execute("""
            INSERT OR REPLACE INTO game_votes (channel_id, voter_id, target_id)
            VALUES (?, ?, ?)
        """, (channel_id, voter_id, target_id))
        await self.connection.commit()
    
    async def get_votes(self, channel_id: int) -> Dict[int, int]:
        """Get all votes (voter_id -> target_id)"""
        if self.connection is None:
            raise ValueError("Database connection not initialized. Call initialize() first.")
        async with self.connection.execute("""
            SELECT voter_id, target_id FROM game_votes WHERE channel_id = ?
        """, (channel_id,)) as cursor:
            rows = await cursor.fetchall()
            return {row['voter_id']: row['target_id'] for row in rows}
    
    async def clear_votes(self, channel_id: int):
        """Clear all votes for a game"""
        if self.connection is None:
            raise ValueError("Database connection not initialized. Call initialize() first.")
        await self.connection.execute("DELETE FROM game_votes WHERE channel_id = ?", (channel_id,))
        await self.connection.commit()
    
    async def set_impostors(self, channel_id: int, user_ids: List[int]):
        """Set the impostors for a game"""
        if self.connection is None:
            raise ValueError("Database connection not initialized. Call initialize() first.")
        await self.connection.execute("DELETE FROM game_impostors WHERE channel_id = ?", (channel_id,))
        
        for user_id in user_ids:
            await self.connection.execute("""
                INSERT INTO game_impostors (channel_id, user_id) VALUES (?, ?)
            """, (channel_id, user_id))
        
        await self.connection.commit()
    
    async def get_impostors(self, channel_id: int) -> List[int]:
        """Get impostor user IDs"""
        if self.connection is None:
            raise ValueError("Database connection not initialized. Call initialize() first.")
        async with self.connection.execute("""
            SELECT user_id FROM game_impostors WHERE channel_id = ?
        """, (channel_id,)) as cursor:
            rows = await cursor.fetchall()
            return [row['user_id'] for row in rows]

    async def init_player_stats(self, user_id: int, username: str):
        """Initialize player stats if they don't exist"""
        if self.connection is None:
            raise ValueError("Database connection not initialized. Call initialize() first.")
        await self.connection.execute("""
            INSERT OR IGNORE INTO player_stats (user_id, username)
            VALUES (?, ?)
        """, (user_id, username))
        await self.connection.commit()
    
    async def update_player_stats(self, user_id: int, **kwargs):
        """Update player statistics"""
        if self.connection is None:
            raise ValueError("Database connection not initialized. Call initialize() first.")
        if not kwargs:
            return
        
        kwargs['updated_at'] = datetime.now().isoformat()
        fields = ", ".join(f"{key} = ?" for key in kwargs.keys())
        values = list(kwargs.values()) + [user_id]
        
        await self.connection.execute(f"""
            UPDATE player_stats SET {fields} WHERE user_id = ?
        """, values)
        await self.connection.commit()
    
    async def increment_stat(self, user_id: int, stat_name: str, amount: int = 1):
        """Increment a player stat"""
        if self.connection is None:
            raise ValueError("Database connection not initialized. Call initialize() first.")
        await self.connection.execute(f"""
            UPDATE player_stats 
            SET {stat_name} = {stat_name} + ?, updated_at = ?
            WHERE user_id = ?
        """, (amount, datetime.now().isoformat(), user_id))
        await self.connection.commit()
    
    async def get_player_stats(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get player statistics"""
        if self.connection is None:
            raise ValueError("Database connection not initialized. Call initialize() first.")
        async with self.connection.execute("""
            SELECT * FROM player_stats WHERE user_id = ?
        """, (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None
    
    async def get_leaderboard(self, stat: str = 'total_games', limit: int = 10) -> List[Dict[str, Any]]:
        """Get leaderboard for a specific stat"""
        if self.connection is None:
            raise ValueError("Database connection not initialized. Call initialize() first.")
        async with self.connection.execute(f"""
            SELECT * FROM player_stats 
            ORDER BY {stat} DESC 
            LIMIT ?
        """, (limit,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    
    async def get_all_active_games(self) -> List[int]:
        """Get all active game channel IDs"""
        if self.connection is None:
            raise ValueError("Database connection not initialized. Call initialize() first.")
        async with self.connection.execute("SELECT channel_id FROM games") as cursor:
            rows = await cursor.fetchall()
            return [row['channel_id'] for row in rows]
