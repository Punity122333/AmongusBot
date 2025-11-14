import random
import asyncio
from typing import List, Dict, Optional, Set
from .tasks import Task, generate_tasks_for_player
from .constants import MIN_PLAYERS, MAX_PLAYERS, PLAYER_COLORS
from .map_renderer import MapLayout


class Player:
    def __init__(self, user_id: int, name: str, avatar_url: str = "", is_bot: bool = False):
        self.user_id = user_id
        self.name = name
        self.avatar_url = avatar_url
        self.is_bot = is_bot
        self.alive = True
        self.role = 'Crewmate'
        self.tasks: List[Task] = []
        self.color = '#FFFFFF'
        self.location = 'Cafeteria'
        self.voted_for: Optional[int] = None
        self.kill_cooldown = 0
        self.sabotage_cooldown = 0
        self.emergency_meetings_left = 1
        self.in_vent = False
        
        # Fast travel counter
        self.fast_travels_remaining = 3
        
        # Bot behavior attributes
        self.suspicion_level = 0  # How suspicious this bot is of others
        self.last_task_time = 0
        self.last_kill_time = 0
        
        self.role_type = 'Crewmate'
        self.can_vent = False
        self.task_speed_multiplier = 1.0
        self.sabotage_fix_speed = 1.0
        
    @property
    def completed_tasks(self) -> int:
        return sum(1 for task in self.tasks if task.completed)
    
    @property
    def total_tasks(self) -> int:
        return len(self.tasks)
    
    @property
    def task_progress(self) -> str:
        return f"{self.completed_tasks}/{self.total_tasks}"

    def assign_role(self, role: str):
        self.role = role
        
        if role == 'Impostor':
            self.role_type = 'Impostor'
            self.can_vent = True
        elif role == 'Scientist':
            self.role_type = 'Scientist'
            self.task_speed_multiplier = 1.5
        elif role == 'Engineer':
            self.role_type = 'Engineer'
            self.can_vent = True
            self.sabotage_fix_speed = 2.0
        else:
            self.role_type = 'Crewmate'

    def assign_tasks(self, task_count: Optional[int] = None):
        """Assign random tasks to player"""
        self.tasks = generate_tasks_for_player(task_count)
    
    def complete_task(self, task_index: int) -> bool:
        """Mark a task as complete"""
        if 0 <= task_index < len(self.tasks):
            self.tasks[task_index].completed = True
            return True
        return False

    def to_dict(self):
        return {
            'id': self.user_id,
            'name': self.name,
            'avatar_url': self.avatar_url,
            'is_bot': self.is_bot,
            'alive': self.alive,
            'role': self.role,
            'role_type': self.role_type,
            'tasks': [str(task) for task in self.tasks],
            'completed_tasks': self.completed_tasks,
            'total_tasks': self.total_tasks,
            'color': self.color,
            'location': self.location,
            'can_vent': self.can_vent,
            'fast_travels_remaining': self.fast_travels_remaining,
        }


class AmongUsGame:
    def __init__(self, guild_id: int, channel_id: int, max_players: int = MAX_PLAYERS):
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.max_players = max_players
        self.players: Dict[int, Player] = {}
        self.phase = 'lobby'
        self.impostors: List[int] = []
        self.min_players = MIN_PLAYERS
        self.votes: Dict[int, int] = {}
        self.game_code = self._generate_game_code()
        self.active_sabotage: Optional[str] = None
        self.kill_cooldown = 18
        self.meeting_cooldown = 0
        self.last_meeting_time = 0
        self.game_start_time = 0
        self.nearby_players_last_meeting: List[str] = []
        
        self.background_tasks: Set[asyncio.Task] = set()
        
        self.map_layout = MapLayout()

    def _generate_game_code(self) -> str:
        """Generate a random 6-letter game code"""
        import string
        return ''.join(random.choices(string.ascii_uppercase, k=6))

    async def add_player(self, user_id: int, name: str, avatar_url: str = "", is_bot: bool = False):
        if len(self.players) >= self.max_players:
            raise ValueError('Room full')
        p = Player(user_id, name, avatar_url, is_bot)
        # Assign color
        p.color = PLAYER_COLORS[len(self.players) % len(PLAYER_COLORS)]
        self.players[user_id] = p
        return p

    async def remove_player(self, user_id: int):
        if user_id in self.players:
            del self.players[user_id]

    async def add_dummies_if_needed(self):
        
        while len(self.players) < self.max_players:
            dummy_id = -(len(self.players) + 1)
            name = f'Dummy{abs(dummy_id)}'
            await self.add_player(dummy_id, name, "", is_bot=True)

    async def assign_roles(self, impostor_count: int = 1, scientists: int = 0, engineers: int = 0):
        ids = list(self.players.keys())
        random.shuffle(ids)
        impostor_count = min(impostor_count, max(1, len(ids) // 3))
        self.impostors = ids[:impostor_count]
        
        # Calculate special role counts
        max_special = max(0, len(ids) - impostor_count)
        scientists = min(scientists, max_special // 2)
        engineers = min(engineers, max_special - scientists)
        
        # Assign roles
        remaining_ids = [uid for uid in ids if uid not in self.impostors]
        random.shuffle(remaining_ids)
        
        scientist_ids = remaining_ids[:scientists]
        engineer_ids = remaining_ids[scientists:scientists + engineers]
        
        for uid, player in self.players.items():
            if uid in self.impostors:
                player.assign_role('Impostor')
                player.assign_tasks()  # Give impostors fake tasks to blend in
            elif uid in scientist_ids:
                player.assign_role('Scientist')
                player.assign_tasks()
            elif uid in engineer_ids:
                player.assign_role('Engineer')
                player.assign_tasks()
            else:
                player.assign_role('Crewmate')
                player.assign_tasks()

    def alive_players(self):
        return [p for p in self.players.values() if p.alive]
    
    def alive_crewmates(self):
        return [p for p in self.alive_players() if p.role in ['Crewmate', 'Scientist', 'Engineer']]
    
    def alive_impostors(self):
        return [p for p in self.alive_players() if p.role == 'Impostor']

    def check_win(self):
        alive = self.alive_players()
        impostors_alive = [p for p in alive if p.role == 'Impostor']
        crewmates_alive = [p for p in alive if p.role in ['Crewmate', 'Scientist', 'Engineer']]
        
        if not impostors_alive:
            return 'crewmates'
        if len(crewmates_alive) <= 1:
            return 'impostors'
        
        # check tasks - all crewmate roles
        all_crew = [p for p in self.players.values() if p.role in ['Crewmate', 'Scientist', 'Engineer']]
        if all_crew:
            total_tasks = sum(p.total_tasks for p in all_crew)
            completed = sum(p.completed_tasks for p in all_crew)
            if total_tasks > 0 and completed >= total_tasks:
                return 'crewmates'
        
        return None
    
    async def cast_vote(self, voter_id: int, target_id: int):
        """Cast a vote during a meeting"""
        if voter_id in self.players and self.players[voter_id].alive:
            self.votes[voter_id] = target_id
    
    async def tally_votes(self) -> Optional[int]:
        """Tally votes and return the player ID with most votes, or None if tie/no votes"""
        if not self.votes:
            return None
        
        # Count votes, excluding skips (-1)
        vote_counts = {}
        for target_id in self.votes.values():
            if target_id != -1:  # Exclude skips from counting
                vote_counts[target_id] = vote_counts.get(target_id, 0) + 1
        
        # If everyone skipped, no one gets ejected
        if not vote_counts:
            return None
        
        # Find max votes
        max_votes = max(vote_counts.values())
        players_with_max = [pid for pid, count in vote_counts.items() if count == max_votes]
        
        # If tie between multiple players, return None (only if 2+ players have same vote count)
        if len(players_with_max) > 1:
            return None
        
        # Return player with most votes (even if it's just 1 or 2 votes - majority wins)
        return players_with_max[0]
    
    async def clear_votes(self):
        """Clear all votes"""
        self.votes = {}
        for player in self.players.values():
            player.voted_for = None
    
    def cancel_all_tasks(self):
        """Cancel all background tasks (called when game ends)"""
        for task in self.background_tasks:
            if not task.done():
                task.cancel()
        self.background_tasks.clear()

    def move_player(self, player_id: int, target_room: str) -> bool:
        if player_id not in self.players:
            return False
        
        player = self.players[player_id]
        current_room = player.location
        
        if not self.map_layout.is_connected(current_room, target_room):
            return False
        
        player.location = target_room
        return True

    def get_room(self, room_name: str):
        return self.map_layout.get_room(room_name)

    def add_body_to_room(self, room_name: str, player_name: str):
        self.map_layout.add_body_to_room(room_name, player_name)

    def get_players_in_room(self, room_name: str) -> List[Player]:
        return [p for p in self.players.values() if p.location == room_name and p.alive]

    def to_summary(self):
        return {
            'guild': self.guild_id,
            'channel': self.channel_id,
            'phase': self.phase,
            'game_code': self.game_code,
            'players': [p.to_dict() for p in self.players.values()],
        }
