"""Game loops for tasks, killing, and AI behavior"""

import discord
import asyncio
import random
from typing import List, Optional
from amongus.core import AmongUsGame
from amongus.map_renderer import MapLayout
from .game_bodies import notify_body_discovery
from .game_meeting import trigger_meeting
from .game_utils import check_and_announce_winner


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
    queue = [(start, [start])]
    
    while queue:
        current, path = queue.pop(0)
        
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


async def start_game_loops(
    bot: discord.Client, game: AmongUsGame, channel: discord.TextChannel
):
    """Start all game loops - individual loops for each bot player"""
    task = asyncio.create_task(debug_body_logger(game, channel))
    if hasattr(game, 'background_tasks'):
        game.background_tasks.add(task)
        task.add_done_callback(lambda t: game.background_tasks.discard(t) if hasattr(game, 'background_tasks') else None)
    
    for player in game.players.values():
        if player.is_bot and player.alive:
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


async def bot_crewmate_behavior(
    bot: discord.Client, game: AmongUsGame, channel: discord.TextChannel, player
):
    """Individual bot crewmate behavior - does tasks randomly"""
    try:
        await asyncio.sleep(random.uniform(5, 15))
        
        while player.alive and game.phase != "ended":
            if game.phase != "tasks":
                await asyncio.sleep(2)
                continue
            
            incomplete_tasks = [i for i, task in enumerate(player.tasks) if not task.completed]
            
            if not incomplete_tasks:
                await asyncio.sleep(5)
                continue
            
            task_index = random.choice(incomplete_tasks)
            task = player.tasks[task_index]
            
            current_location = player.location
            target_location = task.location
            
            if current_location != target_location:
                path = find_shortest_path(game.map_layout, current_location, target_location)
                
                if path and len(path) > 1:
                    for next_room in path[1:]:
                        if game.phase != "tasks" or not player.alive:
                            break
                        
                        player.location = next_room
                        await asyncio.sleep(random.uniform(3, 7))
            
            if game.phase != "tasks" or not player.alive:
                continue
            
            task_time = random.uniform(8, 20) / player.task_speed_multiplier
            await asyncio.sleep(task_time)
            
            if game.phase != "tasks" or not player.alive:
                continue
            
            player.complete_task(task_index)
            
            try:
                await channel.send(
                    f"✅ **{player.name}** completed: {task.task_info['emoji']} "
                    f"{task.task_info['name']} ({player.task_progress})"
                )
            except Exception:
                pass
            
            await check_and_announce_winner(game, channel, "tasks", bot)
            
            idle_time = random.uniform(6, 18)
            await asyncio.sleep(idle_time)
            
    except Exception as e:
        print(f"Error in bot crewmate behavior for {player.name}: {e}")


async def bot_impostor_behavior(
    bot: discord.Client, game: AmongUsGame, channel: discord.TextChannel, player
):
    """Individual bot impostor behavior - moves randomly and kills opportunistically"""
    try:
        await asyncio.sleep(random.uniform(10, 20))
        
        while player.alive and game.phase != "ended":
            if game.phase != "tasks":
                await asyncio.sleep(2)
                continue
            
            if player.kill_cooldown == 0:
                all_crewmates = game.alive_crewmates()
                
                if all_crewmates and random.random() < 0.26:
                    victim = random.choice(all_crewmates)
                    
                    player.location = victim.location
                    
                    await asyncio.sleep(random.uniform(1, 2))
                    
                    if victim.alive and game.phase == "tasks":
                        victim.alive = False
                        player.kill_cooldown = game.kill_cooldown
                        game.add_body_to_room(player.location, victim.name)
                        
                        try:
                            await channel.send(
                                f"💀 **Someone has been killed!** The crew is down to {len(game.alive_players())} players..."
                            )
                        except Exception:
                            pass
                        
                        if not victim.is_bot:
                            try:
                                from amongus.card_generator import create_death_card
                                
                                guild = bot.get_guild(game.guild_id)
                                if guild:
                                    victim_user = guild.get_member(victim.user_id)
                                    if victim_user:
                                        card_buffer = await create_death_card(victim.name, victim.avatar_url)
                                        file = discord.File(card_buffer, filename="death.png")
                                        
                                        embed = discord.Embed(
                                            title="💀 You Have Been Killed!",
                                            description=f"You were eliminated by an impostor.\n\nYou can still help your team by completing tasks as a ghost!",
                                            color=discord.Color.dark_red()
                                        )
                                        embed.set_image(url="attachment://death.png")
                                        
                                        await safe_dm_user(victim_user, embed=embed, file=file)
                            except Exception as e:
                                print(f"Error DMing victim: {e}")
                        
                        
                        report_chance = random.random()
                        
                        if report_chance < 0.25:
                            
                            from .game_bodies import schedule_impostor_self_report
                            asyncio.create_task(schedule_impostor_self_report(bot, game, channel, victim, player, player.location))
                        elif report_chance < 0.50:
                            
                            from .game_bodies import teleport_and_report_body
                            asyncio.create_task(teleport_and_report_body(bot, game, channel, victim, player.location))
                        
                        if await check_and_announce_winner(game, channel, "kill", bot):
                            return
                        
                        await asyncio.sleep(random.uniform(3, 7))
                        continue

            action_roll = random.random()
            
            if action_roll < 0.15 and not game.active_sabotage and player.sabotage_cooldown == 0:
                sabotage_types = ["electrical", "o2", "reactor", "communications"]
                sabotage_type = random.choice(sabotage_types)
                
                game.active_sabotage = sabotage_type
                player.sabotage_cooldown = game.kill_cooldown
                
                sabotage_messages = {
                    "electrical": "🚨 **SABOTAGE!** ⚡ **ELECTRICAL FAILURE**\nCrewmates must fix the lights! Use `/fixsabotage electrical`",
                    "o2": "🚨 **SABOTAGE!** 💨 **O2 DEPLETION**\nCrewmates must restore oxygen! Use `/fixsabotage o2`",
                    "reactor": "🚨 **SABOTAGE!** ☢️ **REACTOR MELTDOWN**\nCrewmates must stabilize the reactor! Use `/fixsabotage reactor`",
                    "communications": "🚨 **SABOTAGE!** 📡 **COMMUNICATIONS DOWN**\nCrewmates must fix communications! Use `/fixsabotage communications`"
                }
                
                try:
                    await channel.send(sabotage_messages.get(sabotage_type, "🚨 **SABOTAGE!**"))
                except Exception:
                    pass
                
                await asyncio.sleep(random.uniform(5, 10))
                continue
            
            elif action_roll < 0.35 and player.kill_cooldown > 30:
                # Do fake tasks to blend in (20% chance, only if cooldown is high)
                incomplete_tasks = [i for i, task in enumerate(player.tasks) if not task.completed]
                
                if incomplete_tasks:
                    task_index = random.choice(incomplete_tasks)
                    task = player.tasks[task_index]
                    
                    current_location = player.location
                    target_location = task.location
                    
                    if current_location != target_location:
                        # Move towards task location (but might get interrupted)
                        path = find_shortest_path(game.map_layout, current_location, target_location)
                        
                        if path and len(path) > 1:
                            # Only move 1-2 rooms, not all the way
                            rooms_to_move = min(random.randint(1, 2), len(path) - 1)
                            for i in range(rooms_to_move):
                                if game.phase != "tasks" or not player.alive:
                                    break
                                
                                player.location = path[i + 1]
                                await asyncio.sleep(random.uniform(3, 6))

                    if player.location == target_location and random.random() < 0.7:
                        if game.phase == "tasks" and player.alive:
                            player.complete_task(task_index)
                            
                            try:
                                await channel.send(
                                    f"✅ **{player.name}** completed: {task.task_info['emoji']} "
                                    f"{task.task_info['name']} ({player.task_progress})"
                                )
                            except Exception:
                                pass
                            
                            await asyncio.sleep(random.uniform(3, 7))
                    continue

            current_room_obj = game.get_room(player.location)
            if current_room_obj and current_room_obj.connected_rooms:
                random_room = random.choice(current_room_obj.connected_rooms)
                player.location = random_room
                await asyncio.sleep(random.uniform(2, 3))
            else:
                await asyncio.sleep(2)
            
    except Exception as e:
        print(f"Error in bot impostor behavior for {player.name}: {e}")


async def dummy_task_loop(game: AmongUsGame, channel: discord.TextChannel):
    """Deprecated - kept for backwards compatibility"""
    pass


async def impostor_kill_loop(
    bot: discord.Client, game: AmongUsGame, channel: discord.TextChannel
):
    """Deprecated - kept for backwards compatibility"""
    pass
