"""Task-related commands for crewmates"""

import discord
from discord import app_commands
from discord.ext import commands
from amongus.tasks import get_task_view
from .game_utils import check_and_announce_winner
from typing import Optional
import asyncio
import random


class TasksCog(commands.Cog):
    """Commands for viewing and completing tasks"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.games = getattr(bot, "amongus_games", {})  # Shared games dict

    async def cog_load(self):
        print("TasksCog loaded")

    @app_commands.command(name="tasks", description="View your task list")
    async def view_tasks(self, interaction: discord.Interaction):
        if interaction.channel is None:
            await interaction.response.send_message(
                "This command must be used in a server channel.", ephemeral=True
            )
            return

        ch_id = interaction.channel.id

        if ch_id not in self.games:
            await interaction.response.send_message(
                "No active game in this channel.", ephemeral=True
            )
            return

        game = self.games[ch_id]
        uid = interaction.user.id

        if uid not in game.players:
            await interaction.response.send_message(
                "You are not in this game.", ephemeral=True
            )
            return

        player = game.players[uid]

        # Check if communications is sabotaged (only affects crewmates, not impostors)
        comms_sabotaged = hasattr(game, 'active_sabotage') and game.active_sabotage == 'communications'
        
        if comms_sabotaged and player.role != 'Impostor':
            await interaction.response.send_message(
                "📡 **COMMUNICATIONS OFFLINE!**\n\n"
                "Your task list is currently unavailable due to the communications sabotage.\n"
                "Help fix the sabotage with `/fixsabotage communications` or wait for it to be resolved!",
                ephemeral=True,
            )
            return

        # Build task list (impostors have fake tasks to blend in)
        task_list = []
        for i, task in enumerate(player.tasks):
            status = "✅" if task.completed else "⬜"
            task_list.append(f"{status} {i+1}. {task}")

        # Create progress bar
        progress_percent = (
            int(player.completed_tasks / player.total_tasks * 100)
            if player.total_tasks > 0
            else 0
        )
        filled = int(progress_percent / 10)  # 10 blocks total
        progress_bar = "█" * filled + "░" * (10 - filled)

        # Add role-specific emoji
        role_emoji = {
            'Crewmate': '👷',
            'Scientist': '🧪',
            'Engineer': '🔧',
            'Impostor': '🔪'
        }.get(player.role, '👷')

        # Different title for impostors
        if player.role == 'Impostor':
            title = f"📋 {player.name}'s Fake Tasks (Impostor)"
            description_text = "\n".join(task_list) if task_list else "No fake tasks assigned yet!"
            color = discord.Color.red()
        else:
            ghost_prefix = "👻 " if not player.alive else ""
            title = f"📋 {ghost_prefix}{player.name}'s Tasks ({player.role})"
            description_text = "\n".join(task_list) if task_list else "No tasks assigned yet!"
            color = discord.Color.purple() if not player.alive else discord.Color.blue()

        embed = discord.Embed(
            title=title,
            description=description_text,
            color=color,
        )
        
        # Add impostor-specific info
        if player.role == 'Impostor':
            embed.add_field(
                name="🔪 Impostor Info",
                value="These are FAKE tasks! Doing them won't help crewmates win.\n"
                      "Use them to blend in and appear less suspicious.",
                inline=False
            )
        
        if not player.alive and player.role != 'Impostor':
            embed.add_field(
                name="👻 Ghost Status",
                value="You're dead, but you can still help the crew win by completing tasks!\n"
                      "Your tasks still contribute to the crew's victory.",
                inline=False
            )
        
        if player.role == 'Scientist':
            embed.add_field(
                name="🧪 Scientist Bonus",
                value="You complete tasks 50% faster!",
                inline=False
            )
        elif player.role == 'Engineer':
            embed.add_field(
                name="🔧 Engineer Bonus",
                value="You can use vents and fix sabotages 2x faster!",
                inline=False
            )
        
        # Show progress bar for non-impostors
        if player.role != 'Impostor':
            embed.add_field(
                name="Progress",
                value=f"`{progress_bar}` {player.task_progress} ({progress_percent}%)",
                inline=False,
            )
        else:
            embed.add_field(
                name="Fake Progress",
                value=f"`{progress_bar}` {player.task_progress} ({progress_percent}%) (not tracked for win)",
                inline=False,
            )

        # Calculate crew total task progress for footer
        crewmates = [p for p in game.players.values() if p.role in ['Crewmate', 'Scientist', 'Engineer']]
        if crewmates:
            total_crew_tasks = sum(p.total_tasks for p in crewmates)
            completed_crew_tasks = sum(p.completed_tasks for p in crewmates)
            embed.set_footer(text=f"Crew Total: {completed_crew_tasks}/{total_crew_tasks}")
        else:
            embed.set_footer(text="Crew Total: 0/0")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="dotask", description="Complete a task interactively")
    @app_commands.describe(
        task_number="The task number from your task list (optional - auto-selects task from current room)"
    )
    async def do_task(self, interaction: discord.Interaction, task_number: Optional[int] = None):
        if interaction.channel is None:
            await interaction.response.send_message(
                "This command must be used in a server channel.", ephemeral=True
            )
            return

        ch_id = interaction.channel.id

        if ch_id not in self.games:
            await interaction.response.send_message(
                "No active game in this channel.", ephemeral=True
            )
            return

        game = self.games[ch_id]
        uid = interaction.user.id

        if uid not in game.players:
            await interaction.response.send_message(
                "You are not in this game.", ephemeral=True
            )
            return

        player = game.players[uid]

        if not player.alive and player.role == 'Impostor':
            await interaction.response.send_message(
                "💀 Dead impostors cannot complete tasks!", ephemeral=True
            )
            return

        if game.phase != "tasks":
            await interaction.response.send_message(
                f"Cannot do tasks during {game.phase} phase!", ephemeral=True
            )
            return

        # If no task number provided, auto-select a task from current room
        if task_number is None:
            current_location = player.location
            available_tasks_indices = [
                i for i, task in enumerate(player.tasks)
                if not task.completed and task.location == current_location
            ]
            
            if not available_tasks_indices:
                # No tasks in current room
                all_incomplete = [i for i, task in enumerate(player.tasks) if not task.completed]
                if not all_incomplete:
                    await interaction.response.send_message(
                        "✅ You have completed all your tasks! Great work!",
                        ephemeral=True
                    )
                    return
                
                # Show available tasks in other locations
                task_locations = {}
                for i in all_incomplete:
                    loc = player.tasks[i].location
                    if loc not in task_locations:
                        task_locations[loc] = []
                    task_locations[loc].append(i + 1)
                
                location_list = "\n".join([f"**{loc}**: Tasks {', '.join(map(str, nums))}" for loc, nums in task_locations.items()])
                
                await interaction.response.send_message(
                    f"❌ No tasks available in **{current_location}**!\n\n"
                    f"📋 Tasks in other rooms:\n{location_list}\n\n"
                    f"💡 Use `/move <room>` to travel to a task location.",
                    ephemeral=True
                )
                return
            
            # Randomly select one of the available tasks
            task_index = random.choice(available_tasks_indices)
            task_number = task_index + 1
            
            # Add a message indicating auto-selection
            auto_selected_msg = f""
        else:
            auto_selected_msg = ""
            task_index = task_number - 1
            
            if task_index < 0 or task_index >= len(player.tasks):
                await interaction.response.send_message(
                    f"Invalid task number! Use `/tasks` to see your task list.",
                    ephemeral=True,
                )
                return

        task = player.tasks[task_index]

        if task.completed:
            await interaction.response.send_message(
                f"✅ You already completed this task!", ephemeral=True
            )
            return

        if player.location != task.location:
            await interaction.response.send_message(
                f"❌ You must be in **{task.location}** to complete this task!\n"
                f"You are currently in **{player.location}**.\n"
                f"Use `/move {task.location}` to travel there (if connected).",
                ephemeral=True
            )
            return

        async def on_task_complete():
            player.complete_task(task_index)

            if interaction.channel and isinstance(
                interaction.channel, discord.TextChannel
            ):
                if player.role == "Impostor":
                    await interaction.channel.send(
                        f"✅ **{player.name}** completed: {task.task_info['emoji']} {task.task_info['name']}! "
                        f"({player.task_progress})"
                    )
                else:
                    ghost_prefix = "👻 " if not player.alive else ""
                    await interaction.channel.send(
                        f"✅ {ghost_prefix}**{player.name}** completed: {task.task_info['emoji']} {task.task_info['name']}! "
                        f"({player.task_progress})"
                    )
                    await check_and_announce_winner(game, interaction.channel, "tasks", self.bot)

        view = get_task_view(task, on_task_complete, interaction.user.id)

        if view:
            await interaction.response.send_message(
                f"{auto_selected_msg}{task.task_info['emoji']} **{task.task_info['name']}** at {task.location}\n"
                f"Complete the task below:",
                view=view,
                ephemeral=True,
            )
        else:
            player.complete_task(task_index)
            await interaction.response.send_message(
                f"{auto_selected_msg}✅ Completed: {task.name}", ephemeral=True
            )
            await on_task_complete()


async def setup(bot: commands.Bot):
    await bot.add_cog(TasksCog(bot))
