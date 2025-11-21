"""Utility functions for game logic"""

import discord
import asyncio
import random
from collections import deque
from typing import List, Optional
from amongus.core import AmongUsGame
from amongus.map_renderer import MapLayout


async def safe_dm_user(user: discord.User | discord.Member, **kwargs):
    for attempt in range(7):
        try:
            await user.send(**kwargs)
            return
        except discord.errors.HTTPException:
            if attempt < 6:
                await asyncio.sleep(3)
            else:
                pass


def find_shortest_path(map_layout: MapLayout, start: str, end: str) -> Optional[List[str]]:
    if start == end:
        return [start]
    
    visited = set()
    queue = deque([(start, [start])])
    
    while queue:
        current, path = queue.popleft()
        
        if current in visited:
            continue
        
        visited.add(current)
        
        room = map_layout.get_room(current)
        if not room:
            continue
        
        for neighbor in room.connected_rooms:
            if neighbor == end:
                return path + [neighbor]
            
            if neighbor not in visited:
                queue.append((neighbor, path + [neighbor]))
    
    return None


def find_path_with_mistakes(map_layout: MapLayout, start: str, end: str) -> Optional[List[str]]:
    """
    Find path from start to end with realistic human-like mistakes:
    - 10% chance of taking one wrong turn with backtrack
    - 5-8% chance of random long detour (2-4 extra rooms)
    - Small chance of random wandering/U-turns
    """
    # Get the optimal path first
    optimal_path = find_shortest_path(map_layout, start, end)
    
    if not optimal_path or len(optimal_path) <= 2:
        # Path too short to make a mistake or no path exists
        return optimal_path
    
    # 5-8% chance of major detour (chaotic wandering)
    detour_chance = random.uniform(0.05, 0.08)
    if random.random() < detour_chance:
        # Take a random detour for 2-4 extra rooms
        detour_length = random.randint(2, 4)
        detour_index = random.randint(1, len(optimal_path) - 2)
        detour_location = optimal_path[detour_index]
        
        # Build a wandering path
        wandering_path = optimal_path[:detour_index + 1].copy()
        current_room = detour_location
        visited_in_detour = {detour_location}
        
        for _ in range(detour_length):
            room = map_layout.get_room(current_room)
            if not room or not room.connected_rooms:
                break
            
            # Prefer unvisited neighbors but allow revisiting for chaos
            unvisited = [r for r in room.connected_rooms if r not in visited_in_detour]
            if unvisited and random.random() < 0.7:
                next_room = random.choice(unvisited)
            else:
                next_room = random.choice(room.connected_rooms)
            
            wandering_path.append(next_room)
            visited_in_detour.add(next_room)
            current_room = next_room
        
        # Find path back to optimal route or directly to end
        path_to_end = find_shortest_path(map_layout, current_room, end)
        if path_to_end and len(path_to_end) > 1:
            wandering_path.extend(path_to_end[1:])
            return wandering_path
    
    # 10% chance to make a simple wrong turn with backtrack
    if random.random() < 0.10:
        # Choose a random point in the path to make a mistake (not start or end)
        mistake_index = random.randint(1, len(optimal_path) - 2)
        mistake_location = optimal_path[mistake_index]
        
        # Get the room at the mistake point
        mistake_room = map_layout.get_room(mistake_location)
        if not mistake_room or not mistake_room.connected_rooms:
            return optimal_path
        
        # Find a wrong room (not the next room in optimal path)
        correct_next_room = optimal_path[mistake_index + 1]
        wrong_options = [room for room in mistake_room.connected_rooms 
                        if room != correct_next_room and room != optimal_path[mistake_index - 1]]
        
        if wrong_options:
            # Pick a random wrong room
            wrong_room = random.choice(wrong_options)
            
            # 30% chance to wander a bit more before backtracking
            path_with_mistake = optimal_path[:mistake_index + 1].copy()
            path_with_mistake.append(wrong_room)
            
            if random.random() < 0.30:
                # Wander 1-2 more rooms before realizing mistake
                current = wrong_room
                for _ in range(random.randint(1, 2)):
                    room = map_layout.get_room(current)
                    if room and room.connected_rooms:
                        next_wander = random.choice([r for r in room.connected_rooms if r != mistake_location])
                        path_with_mistake.append(next_wander)
                        current = next_wander
            
            # Backtrack to mistake point
            path_with_mistake.append(mistake_location)
            # Continue to destination
            path_with_mistake.extend(optimal_path[mistake_index + 1:])
            
            return path_with_mistake
    
    # 5% chance of random U-turn in middle of hallway (go back 1 room then forward again)
    if random.random() < 0.05 and len(optimal_path) >= 4:
        uturn_index = random.randint(2, len(optimal_path) - 2)
        path_with_uturn = optimal_path[:uturn_index + 1].copy()
        path_with_uturn.append(optimal_path[uturn_index - 1])  # Go back
        path_with_uturn.append(optimal_path[uturn_index])      # Go forward again
        path_with_uturn.extend(optimal_path[uturn_index + 1:])
        return path_with_uturn
    
    return optimal_path


async def start_game_loops(
    bot: discord.Client, game: AmongUsGame, channel: discord.TextChannel
):
    """Start all game loops - individual loops for each bot player"""
    from .game_loops import bot_crewmate_behavior, bot_impostor_behavior
    
    task = asyncio.create_task(debug_body_logger(game, channel))
    if hasattr(game, 'background_tasks'):
        game.background_tasks.add(task)
        task.add_done_callback(lambda t: game.background_tasks.discard(t) if hasattr(game, 'background_tasks') else None)
    
    for player in game.players.values():
        if player.is_bot:
            if player.role == "Impostor":
                task = asyncio.create_task(bot_impostor_behavior(bot, game, channel, player))
            else:
                task = asyncio.create_task(bot_crewmate_behavior(bot, game, channel, player))
            
            if hasattr(game, 'background_tasks'):
                game.background_tasks.add(task)
                task.add_done_callback(lambda t: game.background_tasks.discard(t) if hasattr(game, 'background_tasks') else None)


async def debug_body_logger(game: AmongUsGame, channel: discord.TextChannel):
    """Debug loop to print all bodies and their locations every 10 seconds"""
    try:
        while game.phase != "ended":
            await asyncio.sleep(10)
            
            if game.phase != "tasks":
                continue
            
            body_info = []
            for room_name, room in game.map_layout.rooms.items():
                if room.bodies:
                    for body in room.bodies:
                        body_info.append(f"{body} in {room_name}")
            
            if body_info:
                print(f"[DEBUG] Bodies: {', '.join(body_info)}")
            else:
                print("[DEBUG] No bodies on the map")
                
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"Error in debug body logger: {e}")


async def panic_to_sabotage(game, player, sabotage_type: str, is_impostor: bool = False):
    """Bot rushes to sabotage location to fix it (crewmate) or fake panic (impostor)"""
    # Map sabotage types to typical fix locations
    sabotage_locations = {
        "electrical": "Electrical",
        "o2": "O2",
        "reactor": "Reactor",
        "communications": "Communications",
        "doors": None  # Doors don't have a specific location
    }
    
    target_location = sabotage_locations.get(sabotage_type)
    
    if not target_location or player.location == target_location:
        return None  # Already at location or no valid location
    
    # Find path to sabotage location
    path = find_shortest_path(game.map_layout, player.location, target_location)
    
    if not path or len(path) <= 1:
        return None
    
    # Move towards the sabotage location (panic)
    try:
        for next_room in path[1:]:
            if game.phase != "tasks" or not player.alive:
                break
            
            # Stop if sabotage is fixed or changed
            if game.active_sabotage != sabotage_type:
                # Return the location where sabotage was fixed
                return player.location
            
            player.location = next_room
            await asyncio.sleep(random.uniform(2, 4))  # Move faster than normal (panic)
        
        # Return final location if we reached the sabotage location
        return player.location
            
    except Exception as e:
        print(f"Error in panic for {player.name}: {e}")
        return None


async def rush_away_from_location(game, player, from_location: str):
    """Bot rushes away from a location back to their task (after sabotage is fixed)"""
    try:
        # Only rush away if the bot is actually at the sabotage location
        if player.location != from_location:
            return
        
        # Get all rooms that are not the current location
        all_rooms = list(game.map_layout.rooms.keys())
        possible_destinations = [room for room in all_rooms if room != from_location]
        
        if not possible_destinations:
            return
        
        # Pick a random destination to rush to
        target_location = random.choice(possible_destinations)
        
        # Find path away from sabotage location
        path = find_shortest_path(game.map_layout, from_location, target_location)
        
        if not path or len(path) <= 1:
            return
        
        # Move super fast away from the location (1-2 seconds per room)
        for next_room in path[1:min(4, len(path))]:  # Rush for up to 3 rooms
            if game.phase != "tasks" or not player.alive:
                break
            
            player.location = next_room
            await asyncio.sleep(random.uniform(1, 2))  # Super fast movement
            
    except Exception as e:
        print(f"Error in rush away for {player.name}: {e}")


async def cleanup_game(game, bot=None):
    """
    Cleanup a game from both database and cache.
    Properly removes the game from everywhere when it ends.
    """
    try:
        channel_id = game.channel_id
        
        game_manager = None
        
        if bot and hasattr(bot, 'game_manager'):
            game_manager = bot.game_manager
        
        elif hasattr(game, 'db') and game.db:
            from amongus.game_manager import GameManager

            if bot and hasattr(bot, 'amongus_games'):

                if hasattr(bot, 'game_manager'):
                    game_manager = bot.game_manager

        if not game_manager and bot and hasattr(bot, 'amongus_games'):

            if channel_id in bot.amongus_games:
                del bot.amongus_games[channel_id]
                print(f'✅ Removed game from cache for channel {channel_id}')

        if game_manager:
            await game_manager.delete_game(channel_id)
            print(f'✅ Deleted game via game_manager for channel {channel_id}')

        elif hasattr(game, 'db') and game.db:
            await game.db.delete_game(channel_id)
            print(f'✅ Deleted game from database for channel {channel_id}')
            
    except Exception as e:
        print(f'⚠️  Error cleaning up game: {e}')


async def check_and_announce_winner(
    game, channel: discord.TextChannel, context: str = "", bot=None
) -> bool:
    if game.phase == "ended":
        return True

    winner = game.check_win()
    if winner:
        if hasattr(game, 'cancel_all_tasks'):
            game.cancel_all_tasks()
        
        game.active_sabotage = None
        
        game.phase = "ended"

        if winner == "crewmates":
            message = "🎉 **CREWMATES WIN!** 🎉\n"
            if "task" in context.lower():
                message += "All tasks have been completed!"
            elif "impostor" in context.lower():
                message += "All impostors eliminated!"
            else:
                message += "All tasks completed or all impostors eliminated!"
            message += "\n\n🛑 Game has ended. Use `/create` to start a new lobby."
        else:
            message = "💀 **IMPOSTORS WIN!** 💀\n"
            if "kill" in context.lower():
                message += "Impostors have eliminated enough crewmates!"
            elif "sabotage" in context.lower():
                message += context
            else:
                message += "Impostors have taken over the ship!"
            message += "\n\n🛑 Game has ended. Use `/create` to start a new lobby."

        await channel.send(message)
        
        channel_id = game.channel_id
        
        if bot and hasattr(bot, 'game_manager'):
            game_manager = bot.game_manager
            try:
                await game_manager.delete_game(channel_id)
                print(f'✅ Deleted game from database for channel {channel_id}')
            except Exception as e:
                print(f'⚠️  Error deleting game from database: {e}')
        
        if bot and hasattr(bot, 'amongus_games'):
            if channel_id in bot.amongus_games:
                del bot.amongus_games[channel_id]
                print(f'✅ Removed game from cache for channel {channel_id}')
        
        return True

    return False
        
    
