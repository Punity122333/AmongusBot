"""Database-aware game manager that wraps core classes"""
from typing import Optional, Dict, List, cast
from .core import Player, AmongUsGame
from .database import GameDatabase
from .tasks import Task, generate_tasks_for_player
import random


class DatabasePlayer(Player):
    """Player class with database persistence"""
    
    def __init__(self, db: GameDatabase, channel_id: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db = db
        self.channel_id = channel_id
        self.db_id: Optional[int] = None
    
    async def save(self):
        """Save player state to database"""
        await self.db.update_player(
            self.channel_id,
            self.user_id,
            name=self.name,
            avatar_url=self.avatar_url,
            is_bot=int(self.is_bot),
            alive=int(self.alive),
            role=self.role,
            role_type=self.role_type,
            color=self.color,
            location=self.location,
            voted_for=self.voted_for,
            kill_cooldown=self.kill_cooldown,
            sabotage_cooldown=self.sabotage_cooldown,
            emergency_meetings_left=self.emergency_meetings_left,
            in_vent=int(self.in_vent),
            can_vent=int(self.can_vent),
            task_speed_multiplier=self.task_speed_multiplier,
            sabotage_fix_speed=self.sabotage_fix_speed
        )
    
    async def save_tasks(self):
        """Save all tasks to database"""
        if not self.db_id:
            return
        
        for task in self.tasks:
            await self.db.add_task(self.db_id, task.task_type, task.location)
    
    def complete_task(self, task_index: int) -> bool:
        """Mark a task as complete and trigger save"""
        result = super().complete_task(task_index)
        # Note: Task update will be handled separately when needed
        return result


class DatabaseGame(AmongUsGame):
    
    def __init__(self, db: GameDatabase, guild_id: int, channel_id: int, max_players: int = 10, impostors: int = 1, scientists: int = 0, engineers: int = 0):
        super().__init__(guild_id, channel_id, max_players, impostors, scientists, engineers)
        self.db = db
    
    async def save(self):
        """Save game state to database"""
        await self.db.update_game(
            self.channel_id,
            phase=self.phase,
            active_sabotage=self.active_sabotage,
            kill_cooldown=self.kill_cooldown
        )
    
    async def add_player(self, user_id: int, name: str, avatar_url: str = "", is_bot: bool = False):  # type: ignore[override]
        """Add player to game and database"""
        if len(self.players) >= self.max_players:
            raise ValueError('Room full')

        existing_player = await self.db.get_player(self.channel_id, user_id)
        if existing_player:
            p = DatabasePlayer(self.db, self.channel_id, user_id, name, avatar_url, is_bot)
            p.db_id = existing_player['id']
            p.color = existing_player['color']
            p.alive = bool(existing_player['alive'])
            p.role = existing_player['role']
            p.role_type = existing_player['role_type']
            p.location = existing_player['location']
            p.voted_for = existing_player['voted_for']
            p.kill_cooldown = existing_player['kill_cooldown']
            p.sabotage_cooldown = existing_player['sabotage_cooldown']
            p.emergency_meetings_left = existing_player['emergency_meetings_left']
            p.in_vent = bool(existing_player['in_vent'])
            p.can_vent = bool(existing_player['can_vent'])
            p.task_speed_multiplier = existing_player['task_speed_multiplier']
            p.sabotage_fix_speed = existing_player['sabotage_fix_speed']
            
            # Load tasks if player has a db_id
            if p.db_id:
                task_data_list = await self.db.get_player_tasks(p.db_id)
                p.tasks = []
                for t_data in task_data_list:
                    task = Task(t_data['task_type'], t_data['location'])
                    task.completed = bool(t_data['completed'])
                    p.tasks.append(task)
            
            self.players[user_id] = p
            return p
        
        from .constants import PLAYER_COLORS
        color = PLAYER_COLORS[len(self.players) % len(PLAYER_COLORS)]
        
        # Add to database
        await self.db.add_player(
            self.channel_id, user_id, name, avatar_url, is_bot, color
        )
        
        # Create player object
        p = DatabasePlayer(self.db, self.channel_id, user_id, name, avatar_url, is_bot)
        p.color = color
        
        # Get database ID
        player_data = await self.db.get_player(self.channel_id, user_id)
        if player_data:
            p.db_id = player_data['id']
        
        self.players[user_id] = p
        return p
    
    async def remove_player(self, user_id: int):  # type: ignore[override]
        """Remove player from game and database"""
        if user_id in self.players:
            await self.db.remove_player(self.channel_id, user_id)
            del self.players[user_id]
    
    async def add_dummies_if_needed(self):
        while len(self.players) < self.max_players:
            dummy_id = -(len(self.players) + 1)
            name = f'Dummy{abs(dummy_id)}'
            dummy = await self.add_player(dummy_id, name, "", is_bot=True)

            current_impostors = sum(1 for p in self.players.values() if p.role == 'Impostor')
            current_scientists = sum(1 for p in self.players.values() if p.role == 'Scientist')
            current_engineers = sum(1 for p in self.players.values() if p.role == 'Engineer')

            available_roles = []
            
            remaining_impostors = self.impostor_count - current_impostors
            remaining_scientists = self.scientist_count - current_scientists
            remaining_engineers = self.engineer_count - current_engineers
            
            for _ in range(remaining_impostors):
                available_roles.append('Impostor')
            for _ in range(remaining_scientists):
                available_roles.append('Scientist')
            for _ in range(remaining_engineers):
                available_roles.append('Engineer')
            
            remaining_special_slots = remaining_impostors + remaining_scientists + remaining_engineers
            total_assigned = len(self.players)
            remaining_crewmate_slots = self.max_players - total_assigned - remaining_special_slots
            
            for _ in range(remaining_crewmate_slots):
                available_roles.append('Crewmate')
            
            if not available_roles:
                available_roles = ['Crewmate']

            assigned_role = random.choice(available_roles)
            dummy.assign_role(assigned_role)
            dummy.assign_tasks()

            if assigned_role == 'Impostor':
                if dummy_id not in self.impostors:
                    self.impostors.append(dummy_id)

            if hasattr(dummy, 'save'):
                await dummy.save()
                if hasattr(dummy, 'save_tasks') and dummy.db_id:
                    await dummy.save_tasks()
        
        await self.db.set_impostors(self.channel_id, self.impostors)
    
    async def assign_roles(self, impostor_count: int = 1, scientists: int = 0, engineers: int = 0): 
        """Assign roles and save to database"""
        ids = list(self.players.keys())
        random.shuffle(ids)
        impostor_count = min(impostor_count, max(1, len(ids) // 3))
        self.impostors = ids[:impostor_count]
        
        max_special = max(0, len(ids) - impostor_count)
        scientists = min(scientists, max_special // 2)
        engineers = min(engineers, max_special - scientists)
        
        remaining_ids = [uid for uid in ids if uid not in self.impostors]
        random.shuffle(remaining_ids)
        
        scientist_ids = remaining_ids[:scientists]
        engineer_ids = remaining_ids[scientists:scientists + engineers]
        
        for uid, player in self.players.items():
            db_player = cast(DatabasePlayer, player)
            if uid in self.impostors:
                db_player.assign_role('Impostor')
                db_player.assign_tasks()
            elif uid in scientist_ids:
                db_player.assign_role('Scientist')
                db_player.assign_tasks()
            elif uid in engineer_ids:
                db_player.assign_role('Engineer')
                db_player.assign_tasks()
            else:
                db_player.assign_role('Crewmate')
                db_player.assign_tasks()
            
            await db_player.save()
            
            if db_player.db_id and db_player.tasks:
                await db_player.save_tasks()
        
        await self.db.set_impostors(self.channel_id, self.impostors)
    
    async def cast_vote(self, voter_id: int, target_id: int):  # type: ignore[override]
        """Cast a vote and save to database"""
        if voter_id in self.players and self.players[voter_id].alive:
            self.votes[voter_id] = target_id
            await self.db.cast_vote(self.channel_id, voter_id, target_id)
    
    async def clear_votes(self):  # type: ignore[override]
        """Clear all votes from game and database"""
        self.votes = {}
        for player in self.players.values():
            player.voted_for = None
        await self.db.clear_votes(self.channel_id)
    
    @classmethod
    async def load_from_db(cls, db: GameDatabase, channel_id: int) -> Optional['DatabaseGame']:
        """Load a game from the database"""
        game_data = await db.get_game(channel_id)
        if not game_data:
            return None
        
        impostor_count = game_data.get('impostor_count', 1)
        scientist_count = game_data.get('scientist_count', 0)
        engineer_count = game_data.get('engineer_count', 0)
        
        game = cls(db, game_data['guild_id'], channel_id, game_data['max_players'], impostor_count, scientist_count, engineer_count)
        game.phase = game_data['phase']
        game.game_code = game_data['game_code']
        game.min_players = game_data['min_players']
        game.active_sabotage = game_data['active_sabotage']
        game.kill_cooldown = game_data['kill_cooldown']
        
        # Load players
        player_data_list = await db.get_players(channel_id)
        for p_data in player_data_list:
            player = DatabasePlayer(
                db, channel_id,
                p_data['user_id'],
                p_data['name'],
                p_data['avatar_url'],
                bool(p_data['is_bot'])
            )
            player.db_id = p_data['id']
            player.alive = bool(p_data['alive'])
            player.role = p_data['role']
            player.role_type = p_data['role_type']
            player.color = p_data['color']
            player.location = p_data['location']
            player.voted_for = p_data['voted_for']
            player.kill_cooldown = p_data['kill_cooldown']
            player.sabotage_cooldown = p_data['sabotage_cooldown']
            player.emergency_meetings_left = p_data['emergency_meetings_left']
            player.in_vent = bool(p_data['in_vent'])
            player.can_vent = bool(p_data['can_vent'])
            player.task_speed_multiplier = p_data['task_speed_multiplier']
            player.sabotage_fix_speed = p_data['sabotage_fix_speed']
            
            # Load tasks
            if player.db_id is not None:  # Added safety check to ensure db_id is not None
                task_data_list = await db.get_player_tasks(player.db_id)
            else:
                task_data_list = []
            player.tasks = []
            for t_data in task_data_list:
                task = Task(t_data['task_type'], t_data['location'])
                task.completed = bool(t_data['completed'])
                player.tasks.append(task)
            
            game.players[player.user_id] = player
        
        # Load impostors
        game.impostors = await db.get_impostors(channel_id)
        
        # Load votes
        game.votes = await db.get_votes(channel_id)
        
        return game


class GameManager:
    """Manager for all games with database backend"""
    
    def __init__(self, db: GameDatabase):
        self.db = db
        self._cache: Dict[int, DatabaseGame] = {}
    
    async def create_game(self, guild_id: int, channel_id: int, game_code: str, max_players: int = 10, impostors: int = 1, scientists: int = 0, engineers: int = 0) -> DatabaseGame:
        await self.db.create_game(channel_id, guild_id, game_code, max_players, impostors, scientists, engineers)
        
        game = DatabaseGame(self.db, guild_id, channel_id, max_players, impostors, scientists, engineers)
        game.game_code = game_code
        
        self._cache[channel_id] = game
        
        return game
    
    async def get_game(self, channel_id: int) -> Optional[DatabaseGame]:
        """Get a game (from cache or database)"""
        # Check cache first
        if channel_id in self._cache:
            return self._cache[channel_id]
        
        # Load from database
        game = await DatabaseGame.load_from_db(self.db, channel_id)
        if game:
            self._cache[channel_id] = game
        
        return game
    
    async def get_game_by_code(self, game_code: str) -> Optional[tuple[int, DatabaseGame]]:
        """Find game by code"""
        game_data = await self.db.get_game_by_code(game_code)
        if not game_data:
            return None
        
        channel_id = game_data['channel_id']
        game = await self.get_game(channel_id)
        return (channel_id, game) if game else None
    
    async def delete_game(self, channel_id: int):
        """Delete a game"""
        await self.db.delete_game(channel_id)
        if channel_id in self._cache:
            del self._cache[channel_id]
    
    async def game_exists(self, channel_id: int) -> bool:
        """Check if game exists"""
        if channel_id in self._cache:
            return True
        return await self.db.game_exists(channel_id)
    
    def __getitem__(self, channel_id: int) -> Optional[DatabaseGame]:
        """Get game from cache (synchronous, for backward compatibility)"""
        return self._cache.get(channel_id)
    
    def __contains__(self, channel_id: int) -> bool:
        """Check if game is in cache"""
        return channel_id in self._cache
