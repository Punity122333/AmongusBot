"""Game start and initialization commands"""

import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from amongus.core import AmongUsGame
from amongus.card_generator import create_role_reveal_card
from typing import cast


class GameStartCog(commands.Cog):
    """Commands for starting games"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.games = getattr(bot, "amongus_games", {})

    async def cog_load(self):
        print("GameStartCog loaded")

    @app_commands.command(
        name="start", description="Start the game (assign roles, begin tasks)"
    )
    @app_commands.describe(
        impostors="Number of impostors (default: 1, max: 1/3 of players)",
        scientists="Number of Scientists (faster tasks)",
        engineers="Number of Engineers (can vent, fix sabotages faster)"
    )
    async def start(
        self, 
        interaction: discord.Interaction, 
        impostors: int = 1,
        scientists: int = 0,
        engineers: int = 0
    ):
        if interaction.guild is None or interaction.channel is None:
            await interaction.response.send_message(
                "This command must be used in a server text channel.", ephemeral=True
            )
            return

        await interaction.response.defer(thinking=True)
        ch_id = interaction.channel.id

        if ch_id not in self.games:
            await interaction.followup.send("No lobby in this channel.", ephemeral=True)
            return

        game = self.games[ch_id]

        if game.phase != "lobby":
            await interaction.followup.send("Game already started!", ephemeral=True)
            return

        # # Check if we have enough real players
        # if len(game.players) < game.min_players:
        #     await interaction.followup.send(
        #         f"❌ Not enough players! Need at least {game.min_players} players to start. "
        #         f"Currently have {len(game.players)}.",
        #         ephemeral=True,
        #     )
        #     return
        # Validate impostor count
        
        max_impostors = max(1, game.max_players // 3)
        if impostors < 1:
            await interaction.followup.send(
                "❌ Must have at least 1 impostor!", ephemeral=True
            )
            return

        if impostors > max_impostors:
            await interaction.followup.send(
                f"❌ Too many impostors! Maximum for {game.max_players} players is {max_impostors}.",
                ephemeral=True,
            )
            return

        await game.add_dummies_if_needed()

        # Assign roles with special roles
        await game.assign_roles(impostor_count=impostors, scientists=scientists, engineers=engineers)
        game.phase = "tasks"
        
        import time
        game.game_start_time = time.time()
        
        # Set initial kill cooldown to 35 seconds for all impostors
        for player in game.players.values():
            if player.role == "Impostor":
                player.kill_cooldown = 90
                player.sabotage_cooldown = 90

        # Count special roles
        scientist_count = sum(1 for p in game.players.values() if p.role == 'Scientist')
        engineer_count = sum(1 for p in game.players.values() if p.role == 'Engineer')

        role_summary = f"🎮 **Game Started!**\n" \
                      f"Players: {len(game.players)}\n" \
                      f"🔪 Impostors: {len(game.impostors)}\n"
        
        if scientist_count > 0:
            role_summary += f"🧪 Scientists: {scientist_count}\n"
        if engineer_count > 0:
            role_summary += f"🔧 Engineers: {engineer_count}\n"
        
        role_summary += "\nCheck your DMs for your role!"

        await interaction.followup.send(role_summary)

        # DM roles to players
        await self._send_role_dms(interaction, game)

        # Start game loops
        from .game_loops import start_game_loops

        await start_game_loops(
            self.bot, game, cast(discord.TextChannel, interaction.channel)
        )

    async def _send_role_dms(self, interaction: discord.Interaction, game: AmongUsGame):
        """Send role DMs to all players"""
        for p in game.players.values():
            if p.is_bot:
                continue

            user = (
                interaction.guild.get_member(p.user_id) if interaction.guild else None
            )
            if user:
                try:
                    card_buffer = await create_role_reveal_card(
                        p.name, p.avatar_url, p.role, p.total_tasks
                    )

                    file = discord.File(card_buffer, filename="role.png")

                    embed = discord.Embed(
                        title="🎭 Your Role",
                        color=(
                            discord.Color.red()
                            if p.role == "Impostor"
                            else discord.Color.blue()
                        ),
                    )
                    embed.set_image(url="attachment://role.png")

                    if p.role == "Impostor":
                        # Get other impostors
                        other_impostors = [
                            pl.name for pl in game.players.values() 
                            if pl.role == "Impostor" and pl.user_id != p.user_id
                        ]
                        
                        teammates_text = ""
                        if other_impostors:
                            teammates_text = f"\n\n🤝 **Fellow Impostor(s):**\n" + "\n".join(f"• {name}" for name in other_impostors)
                        
                        embed.description = (
                            "🔪 **You are an Impostor!**\n\n"
                            "Your goal is to eliminate all crewmates.\n"
                            "You will automatically kill nearby players.\n"
                            f"Sabotage and deceive to win!{teammates_text}"
                        )
                    elif p.role == "Scientist":
                        task_list = "\n".join(
                            [f"• {task.name}" for task in p.tasks[:5]]
                        )
                        if len(p.tasks) > 5:
                            task_list += f"\n... and {len(p.tasks) - 5} more"

                        embed.description = (
                            f"🧪 **You are a Scientist!**\n\n"
                            f"Special Ability: **50% faster task completion!**\n\n"
                            f"Complete your {p.total_tasks} tasks to win!\n\n"
                            f"**Your Tasks:**\n{task_list}\n\n"
                            f"Use `/tasks` to view all tasks\n"
                            f"Use `/dotask <number>` to complete tasks"
                        )
                    elif p.role == "Engineer":
                        task_list = "\n".join(
                            [f"• {task.name}" for task in p.tasks[:5]]
                        )
                        if len(p.tasks) > 5:
                            task_list += f"\n... and {len(p.tasks) - 5} more"

                        embed.description = (
                            f"🔧 **You are an Engineer!**\n\n"
                            f"Special Abilities:\n"
                            f"• Can use vents like impostors!\n"
                            f"• Fix sabotages 2x faster!\n\n"
                            f"Complete your {p.total_tasks} tasks to win!\n\n"
                            f"**Your Tasks:**\n{task_list}\n\n"
                            f"Use `/tasks` to view all tasks\n"
                            f"Use `/dotask <number>` to complete tasks\n"
                            f"Use `/vent` to enter/exit vents"
                        )
                    else:
                        task_list = "\n".join(
                            [f"• {task.name}" for task in p.tasks[:5]]
                        )
                        if len(p.tasks) > 5:
                            task_list += f"\n... and {len(p.tasks) - 5} more"

                        embed.description = (
                            f"🔧 **You are a Crewmate!**\n\n"
                            f"Complete your {p.total_tasks} tasks to win!\n\n"
                            f"**Your Tasks:**\n{task_list}\n\n"
                            f"Use `/tasks` to view all tasks\n"
                            f"Use `/dotask <number>` to complete tasks"
                        )

                    await user.send(embed=embed, file=file)
                except Exception as e:
                    print(f"Failed to DM {user}: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(GameStartCog(bot))
