"""Game loops for tasks, killing, and AI behavior"""

import discord
import asyncio
import random
from amongus.core import AmongUsGame
from .game_bodies import notify_body_discovery
from .game_meeting import trigger_meeting
from .game_utils import (
    check_and_announce_winner,
    safe_dm_user,
    find_shortest_path,
    find_path_with_mistakes,
    panic_to_sabotage,
    rush_away_from_location
)


async def bot_crewmate_behavior(
    bot: discord.Client, game: AmongUsGame, channel: discord.TextChannel, player
):
    try:
        await asyncio.sleep(random.uniform(5, 15))
        
        last_sabotage = None
        sabotage_location = None
        
        while game.phase != "ended":
            if game.phase != "tasks":
                await asyncio.sleep(2)
                continue
            
            if random.random() < 0.05:
                await asyncio.sleep(random.uniform(3, 5))
                continue
            
            if random.random() < 0.05:
                other_alive = [p for p in game.alive_players() if p.user_id != player.user_id]
                if other_alive:
                    target_player = random.choice(other_alive)
                    follow_duration = random.randint(2, 4)
                    
                    for _ in range(follow_duration):
                        if game.phase != "tasks" or not player.alive:
                            break
                        
                        if player.location != target_player.location:
                            path = find_shortest_path(game.map_layout, player.location, target_player.location)
                            if path and len(path) > 1:
                                player.location = path[1]
                                await asyncio.sleep(random.uniform(2, 4))
                        else:
                            await asyncio.sleep(random.uniform(1, 3))
                    continue
            
            if game.active_sabotage and game.active_sabotage != last_sabotage:
                if random.random() < 0.75:
                    sabotage_location = await panic_to_sabotage(game, player, game.active_sabotage, is_impostor=False)
                last_sabotage = game.active_sabotage
            elif not game.active_sabotage and last_sabotage:
                if sabotage_location:
                    await rush_away_from_location(game, player, sabotage_location)
                    sabotage_location = None
                last_sabotage = None
            
            incomplete_tasks = [i for i, task in enumerate(player.tasks) if not task.completed]
            
            if not incomplete_tasks:
                await asyncio.sleep(5)
                continue
            
            task_index = random.choice(incomplete_tasks)
            task = player.tasks[task_index]
            
            current_location = player.location
            target_location = task.location
            
            if current_location != target_location:
                path = find_path_with_mistakes(game.map_layout, current_location, target_location)
                
                if path and len(path) > 1:
                    for next_room in path[1:]:
                        if game.phase != "tasks":
                            break
                        
                        player.location = next_room
                        await asyncio.sleep(random.uniform(3, 7))
                        
                        room_obj = game.get_room(next_room)
                        if room_obj and room_obj.bodies and game.phase == "tasks" and player.alive:
                            import time
                            time_since_last_report = time.time() - game.last_body_report_time
                            
                            if random.random() < 0.40 and time_since_last_report >= 10:
                                body_name = room_obj.bodies[0]
                                victim_player = next((p for p in game.players.values() if p.name == body_name), None)
                                
                                if victim_player:
                                    nearby_players = []
                                    from .game_bodies import _get_nearby_players
                                    nearby_players = _get_nearby_players(game, victim_player, player)
                                    
                                    game.nearby_players_last_meeting = nearby_players
                                    
                                    room_obj.remove_body(body_name)
                                    
                                    game.last_body_report_time = time.time()
                                    
                                    await channel.send(
                                        f"👁️ **{player.name}** discovered **{body_name}'s** body in **{next_room}** and called a meeting!"
                                    )
                                    
                                    if nearby_players:
                                        players_list = ", ".join([f"**{p}**" for p in nearby_players])
                                        await channel.send(
                                            f"🗣️ **{player.name}** says: \"I saw {players_list} near the body!\""
                                        )
                                    else:
                                        await channel.send(
                                            f"🗣️ **{player.name}** says: \"The area seemed empty when I found the body.\""
                                        )
                                    
                                    await trigger_meeting(game, channel, f"{player.name} (found body)", bot)
                                    break
            
            if game.phase != "tasks":
                continue
            
            if random.random() < 0.25:
                await asyncio.sleep(random.uniform(1.5, 4))
                
            task_time = random.uniform(8, 20) / player.task_speed_multiplier
            await asyncio.sleep(task_time)
            
            if game.phase != "tasks":
                continue
            
            player.complete_task(task_index)
            
            try:
                prefix = "👻 " if not player.alive else ""
                await channel.send(
                    f"{prefix}✅ **{player.name}** completed: {task.task_info['emoji']} "
                    f"{task.task_info['name']} ({player.task_progress})"
                )
            except Exception:
                pass
            
            await check_and_announce_winner(game, channel, "tasks", bot)
            
            if player.role == 'Guardian Angel' and player.shields_remaining > 0 and player.shield_cooldown == 0:
                if random.random() < 0.15:
                    alive_players = [p for p in game.players.values() if p.alive and not hasattr(p, 'shielded') or not p.shielded]
                    if alive_players:
                        target = random.choice(alive_players)
                        target.shielded = True
                        target.shielded_by = player.user_id
                        player.shields_remaining -= 1
                        player.shield_cooldown = 60
            
            idle_time = random.uniform(6, 18)
            await asyncio.sleep(idle_time)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"Error in bot crewmate behavior for {player.name}: {e}")


async def bot_impostor_behavior(
    bot: discord.Client, game: AmongUsGame, channel: discord.TextChannel, player
):
    try:
        await asyncio.sleep(random.uniform(10, 20))
        
        last_sabotage = None
        sabotage_location = None
        
        while player.alive and game.phase != "ended":
            if game.phase != "tasks":
                await asyncio.sleep(2)
                continue
            
            if random.random() < 0.05:
                await asyncio.sleep(random.uniform(3, 5))
                continue
            
            if random.random() < 0.05 and player.kill_cooldown > 10:
                crewmates = game.alive_crewmates()
                if crewmates:
                    target_player = random.choice(crewmates)
                    stalk_duration = random.randint(2, 4)
                    
                    for _ in range(stalk_duration):
                        if game.phase != "tasks" or not player.alive:
                            break
                        
                        if player.location != target_player.location:
                            path = find_shortest_path(game.map_layout, player.location, target_player.location)
                            if path and len(path) > 1:
                                player.location = path[1]
                                await asyncio.sleep(random.uniform(2, 4))
                        else:
                            await asyncio.sleep(random.uniform(1, 3))
                    continue
            
            if game.active_sabotage and game.active_sabotage != last_sabotage:
                if random.random() < 0.30:
                    sabotage_location = await panic_to_sabotage(game, player, game.active_sabotage, is_impostor=True)
                last_sabotage = game.active_sabotage
            elif not game.active_sabotage and last_sabotage:
                if sabotage_location:
                    await rush_away_from_location(game, player, sabotage_location)
                    sabotage_location = None
                last_sabotage = None
            
            if player.kill_cooldown == 0:
                all_crewmates = game.alive_crewmates()
                
                import time
                time_since_last_kill = time.time() - game.last_kill_time
                
                if all_crewmates and random.random() < 0.25 and time_since_last_kill >= 8:
                    victim = random.choice(all_crewmates)
                    
                    original_location = player.location
                    
                    path_to_victim = find_shortest_path(game.map_layout, player.location, victim.location)
                    if path_to_victim and len(path_to_victim) > 1:
                        player.location = path_to_victim[1]
                        await asyncio.sleep(random.uniform(2, 4))
                    
                    player.location = victim.location
                    
                    await asyncio.sleep(random.uniform(1, 2))
                    
                    if victim.alive and game.phase == "tasks" and time_since_last_kill >= 8:
                        victim.alive = False
                        player.kill_cooldown = game.kill_cooldown
                        game.add_body_to_room(player.location, victim.name)
                        kill_location = player.location
                        
                        import time
                        game.last_kill_time = time.time()
                        
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
                        
                        if report_chance < 0.30:
                            from .game_bodies import schedule_impostor_self_report
                            asyncio.create_task(schedule_impostor_self_report(bot, game, channel, victim, player, kill_location))
                        elif report_chance < 0.70:
                            from .game_bodies import teleport_and_report_body
                            asyncio.create_task(teleport_and_report_body(bot, game, channel, victim, kill_location))
                        
                        current_room_obj = game.get_room(player.location)
                        if current_room_obj and current_room_obj.connected_rooms:
                            for _ in range(random.randint(2, 3)):
                                if game.phase != "tasks" or not player.alive:
                                    break
                                
                                room_obj = game.get_room(player.location)
                                if room_obj and room_obj.connected_rooms:
                                    player.location = random.choice(room_obj.connected_rooms)
                                    await asyncio.sleep(random.uniform(1, 1.5))
                        
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
            
            elif action_roll < 0.40 and player.kill_cooldown > 30:
                
                incomplete_tasks = [i for i, task in enumerate(player.tasks) if not task.completed]
                
                if incomplete_tasks:
                    task_index = random.choice(incomplete_tasks)
                    task = player.tasks[task_index]
                    
                    current_location = player.location
                    target_location = task.location
                    
                    if current_location != target_location:
                        path = find_path_with_mistakes(game.map_layout, current_location, target_location)
                        
                        if path and len(path) > 1:
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

    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"Error in bot impostor behavior for {player.name}: {e}")
