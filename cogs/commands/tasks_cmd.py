"""Task-related commands for crewmates"""

import discord
from discord import app_commands
from discord.ext import commands
from amongus.tasks import get_task_view
from .game_utils import check_and_announce_winner
import asyncio


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
            title = f"📋 {player.name}'s Tasks ({player.role})"
            description_text = "\n".join(task_list) if task_list else "No tasks assigned yet!"
            color = discord.Color.blue()

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
        
        # Add role-specific bonus info
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

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="dotask", description="Complete a task interactively")
    @app_commands.describe(
        task_number="The task number from your task list (use /tasks to view)"
    )
    async def do_task(self, interaction: discord.Interaction, task_number: int):
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

        if not player.alive:
            await interaction.response.send_message(
                "💀 You are dead and cannot complete tasks!", ephemeral=True
            )
            return

        if game.phase != "tasks":
            await interaction.response.send_message(
                f"Cannot do tasks during {game.phase} phase!", ephemeral=True
            )
            return

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
                await interaction.channel.send(
                    f"✅ **{player.name}** completed: {task.task_info['emoji']} {task.task_info['name']}! "
                    f"({player.task_progress})"
                )

                if player.role != "Impostor":
                    await check_and_announce_winner(game, interaction.channel, "tasks", self.bot)

        view = get_task_view(task, on_task_complete)

        if view:
            await interaction.response.send_message(
                f"{task.task_info['emoji']} **{task.task_info['name']}** at {task.location}\n"
                f"Complete the task below:",
                view=view,
                ephemeral=True,
            )
        else:
            player.complete_task(task_index)
            await interaction.response.send_message(
                f"✅ Completed: {task.name}", ephemeral=True
            )
            await on_task_complete()


async def setup(bot: commands.Bot):
    await bot.add_cog(TasksCog(bot))
