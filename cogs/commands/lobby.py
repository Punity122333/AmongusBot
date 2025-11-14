"""Lobby management commands"""

import discord
from discord import app_commands
from discord.ext import commands
from amongus.game_manager import GameManager
from amongus.card_generator import create_lobby_card
from typing import Optional


class LobbyCog(commands.Cog):
    """Commands for creating and managing lobbies"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.games = getattr(bot, "amongus_games", {})  # Shared games dict (cache)
        self.game_manager: Optional[GameManager] = None  # Will be set in cog_load

    async def cog_load(self):
        if hasattr(self.bot, 'game_manager') and getattr(self.bot, 'game_manager', None) is not None:
            self.game_manager = getattr(self.bot, 'game_manager')
        else:
            # Initialize game manager if not present
            from amongus.database import GameDatabase
            if not hasattr(self.bot, 'db') or getattr(self.bot, 'db', None) is None:
                # Initialize database if needed
                db = GameDatabase("amongus.db")
                await db.initialize()
                setattr(self.bot, 'db', db)
            
            # Create game manager
            self.game_manager = GameManager(getattr(self.bot, 'db'))
            setattr(self.bot, 'game_manager', self.game_manager)
            
            # Update cache reference
            setattr(self.bot, 'amongus_games', self.game_manager._cache)
            
        print("LobbyCog loaded")

    @app_commands.command(
        name="create", description="Create an Among Us lobby in this channel"
    )
    @app_commands.describe(
        max_players="Maximum number of players (default: 10, range: 4-15)"
    )
    async def create(self, interaction: discord.Interaction, max_players: int = 10):
        if interaction.guild is None or interaction.channel is None:
            await interaction.response.send_message(
                "This command must be used in a server text channel.", ephemeral=True
            )
            return

        if self.game_manager is None:
            await interaction.response.send_message(
                "Game manager not initialized.", ephemeral=True
            )
            return

        await interaction.response.defer(thinking=True)
        ch_id = interaction.channel.id

        # Check if game already exists
        if await self.game_manager.game_exists(ch_id):
            await interaction.followup.send(
                "A game already exists in this channel.", ephemeral=True
            )
            return

        if max_players < 4:
            await interaction.followup.send(
                "❌ Maximum players must be at least 4!", ephemeral=True
            )
            return

        if max_players > 15:
            await interaction.followup.send(
                "❌ Maximum players cannot exceed 15!", ephemeral=True
            )
            return

        # Generate game code
        import string
        import random
        game_code = ''.join(random.choices(string.ascii_uppercase, k=6))
        
        # Create game in database
        game = await self.game_manager.create_game(
            interaction.guild.id, ch_id, game_code, max_players
        )

        await interaction.followup.send(
            f"🚀 **Among Us Lobby Created!**\n"
            f"Game Code: `{game.game_code}`\n"
            f"Max Players: **{max_players}**\n"
            f"Players can join with `/join {game.game_code}`\n"
            f"Start the game with `/start` when ready!"
        )

    @app_commands.command(name="join", description="Join the Among Us lobby")
    @app_commands.describe(code="The 6-letter game code")
    async def join(self, interaction: discord.Interaction, code: str):
        if interaction.guild is None or interaction.channel is None:
            await interaction.response.send_message(
                "This command must be used in a server text channel.", ephemeral=True
            )
            return

        if self.game_manager is None:
            await interaction.response.send_message(
                "Game manager not initialized.", ephemeral=True
            )
            return

        await interaction.response.defer(thinking=True)

        # Find game by code from database
        result = await self.game_manager.get_game_by_code(code)
        
        if result is None:
            await interaction.followup.send(
                f"❌ No lobby found with code `{code.upper()}`", ephemeral=True
            )
            return
        
        game_channel_id, game = result
        uid = interaction.user.id

        if uid in game.players:
            await interaction.followup.send("You already joined.", ephemeral=True)
            return

        try:
            avatar_url = interaction.user.display_avatar.url
            await game.add_player(uid, interaction.user.display_name, avatar_url)

            player_count = len(game.players)
            await interaction.followup.send(
                f"✅ **{interaction.user.display_name}** joined the lobby! "
                f"({player_count}/{game.max_players} players)"
            )
        except ValueError as e:
            await interaction.followup.send(str(e), ephemeral=True)

    @app_commands.command(name="leave", description="Leave the Among Us lobby")
    async def leave(self, interaction: discord.Interaction):
        if interaction.guild is None or interaction.channel is None:
            await interaction.response.send_message(
                "This command must be used in a server text channel.", ephemeral=True
            )
            return

        if self.game_manager is None:
            await interaction.response.send_message(
                "Game manager not initialized.", ephemeral=True
            )
            return

        ch_id = interaction.channel.id

        game = await self.game_manager.get_game(ch_id)
        if not game:
            await interaction.response.send_message(
                "No lobby in this channel.", ephemeral=True
            )
            return

        uid = interaction.user.id

        if uid not in game.players:
            await interaction.response.send_message(
                "You are not in the lobby.", ephemeral=True
            )
            return

        await game.remove_player(uid)
        await interaction.response.send_message(
            f"👋 **{interaction.user.display_name}** left the lobby."
        )

    @app_commands.command(
        name="viewlobby", description="View the current lobby with player list"
    )
    async def viewlobby(self, interaction: discord.Interaction):
        if interaction.guild is None or interaction.channel is None:
            await interaction.response.send_message(
                "This command must be used in a server text channel.", ephemeral=True
            )
            return

        if self.game_manager is None:
            await interaction.response.send_message(
                "Game manager not initialized.", ephemeral=True
            )
            return

        await interaction.response.defer(thinking=True)
        ch_id = interaction.channel.id

        game = await self.game_manager.get_game(ch_id)
        if not game:
            await interaction.followup.send(
                "No lobby in this channel. Create one with `/create`", ephemeral=True
            )
            return

        # Generate lobby card
        players_data = [p.to_dict() for p in game.players.values()]
        card_buffer = await create_lobby_card(players_data, game.game_code)

        file = discord.File(card_buffer, filename="lobby.png")

        # Create embed
        embed = discord.Embed(
            title="🚀 Among Us Lobby",
            description=f"**Game Code:** `{game.game_code}`\n**Phase:** {game.phase.title()}",
            color=discord.Color.blue(),
        )
        embed.add_field(
            name="Players", value=f"{len(game.players)}/{game.max_players}", inline=True
        )
        embed.set_image(url="attachment://lobby.png")

        await interaction.followup.send(embed=embed, file=file)


async def setup(bot: commands.Bot):
    await bot.add_cog(LobbyCog(bot))
