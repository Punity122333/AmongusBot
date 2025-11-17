"""Game start and initialization commands"""

import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from typing import cast


class GameStartCog(commands.Cog):
    """Commands for starting games"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.games = getattr(bot, "amongus_games", {})


    @app_commands.command(
        name="start", description="Start the game"
    )
    async def start(
        self, 
        interaction: discord.Interaction
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

        await game.add_dummies_if_needed()
        
        import random
        all_rooms = list(game.map_layout.rooms.keys())
        available_rooms = all_rooms.copy()
        
        for player in game.players.values():
            if not player.is_bot:
                if available_rooms:
                    spawn_room = random.choice(available_rooms)
                    available_rooms.remove(spawn_room)
                else:
                    spawn_room = random.choice(all_rooms)
                
                player.location = spawn_room

        game.phase = "tasks"
        
        import time
        game.game_start_time = time.time()
        
        for player in game.players.values():
            if player.role == "Impostor":
                player.kill_cooldown = 90
                player.sabotage_cooldown = 90

        scientist_count = sum(1 for p in game.players.values() if p.role == 'Scientist')
        engineer_count = sum(1 for p in game.players.values() if p.role == 'Engineer')
        impostor_count = sum(1 for p in game.players.values() if p.role == 'Impostor')

        role_summary = f"🎮 **Game Started!**\n" \
                      f"Players: {len(game.players)}\n" \
                      f"🔪 Impostors: {impostor_count}\n"
        
        if scientist_count > 0:
            role_summary += f"🧪 Scientists: {scientist_count}\n"
        if engineer_count > 0:
            role_summary += f"🔧 Engineers: {engineer_count}\n"

        await interaction.followup.send(role_summary)

        from .game_loops import start_game_loops

        await start_game_loops(
            self.bot, game, cast(discord.TextChannel, interaction.channel)
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(GameStartCog(bot))
