"""Lobby management commands"""

import discord
from discord import app_commands
from discord.ext import commands
from amongus.game_manager import GameManager, DatabasePlayer
from amongus.card_generator import (
    create_lobby_card,
    create_role_reveal_card
)
from typing import Optional, cast


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
        max_players="Maximum number of players (default: 10)",
        impostors="Number of impostors (default: 1)",
        scientists="Number of Scientists (default: 0)",
        engineers="Number of Engineers (default: 0)",
        guardian_angels="Number of Guardian Angels (default: 0)"
    )
    async def create(self, interaction: discord.Interaction, max_players: int = 10, impostors: int = 1, scientists: int = 0, engineers: int = 0, guardian_angels: int = 0):
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

        if await self.game_manager.game_exists(ch_id):
            await interaction.followup.send(
                "A game already exists in this channel.", ephemeral=True
            )
            return

        if max_players < 1:
            await interaction.followup.send(
                "❌ Maximum players must be at least 1!", ephemeral=True
            )
            return

        if impostors < 0 or scientists < 0 or engineers < 0 or guardian_angels < 0:
            await interaction.followup.send(
                "❌ Role counts cannot be negative!", ephemeral=True
            )
            return

        total_special_roles = impostors + scientists + engineers + guardian_angels
        if total_special_roles > max_players:
            await interaction.followup.send(
                f"❌ Total special roles ({total_special_roles}) exceeds max players ({max_players})!",
                ephemeral=True
            )
            return

        import string
        import random
        game_code = ''.join(random.choices(string.ascii_uppercase, k=6))
        
        game = await self.game_manager.create_game(
            interaction.guild.id, ch_id, game_code, max_players, impostors, scientists, engineers, guardian_angels
        )

        crewmate_count = max_players - total_special_roles
        
        await interaction.followup.send(
            f"🚀 **Among Us Lobby Created!**\n"
            f"Game Code: `{game.game_code}`\n"
            f"Max Players: **{max_players}**\n"
            f"🔪 Impostors: **{impostors}**\n"
            f"🧪 Scientists: **{scientists}**\n"
            f"🔧 Engineers: **{engineers}**\n"
            f"😇 Guardian Angels: **{guardian_angels}**\n"
            f"👷 Crewmates: **{crewmate_count}**\n\n"
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

        await interaction.response.defer(ephemeral=True)

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
            import random
            avatar_url = interaction.user.display_avatar.url
            await game.add_player(uid, interaction.user.display_name, avatar_url)

            player = cast(DatabasePlayer, game.players[uid])

            current_impostors = sum(1 for p in game.players.values() if p.role == 'Impostor')
            current_scientists = sum(1 for p in game.players.values() if p.role == 'Scientist')
            current_engineers = sum(1 for p in game.players.values() if p.role == 'Engineer')
            current_guardian_angels = sum(1 for p in game.players.values() if p.role == 'Guardian Angel')

            available_roles = []
            
            remaining_impostors = game.impostor_count - current_impostors
            remaining_scientists = game.scientist_count - current_scientists
            remaining_engineers = game.engineer_count - current_engineers
            remaining_guardian_angels = game.guardian_angel_count - current_guardian_angels
            
            for _ in range(remaining_impostors):
                available_roles.append('Impostor')
            for _ in range(remaining_scientists):
                available_roles.append('Scientist')
            for _ in range(remaining_engineers):
                available_roles.append('Engineer')
            for _ in range(remaining_guardian_angels):
                available_roles.append('Guardian Angel')
            
            remaining_special_slots = remaining_impostors + remaining_scientists + remaining_engineers + remaining_guardian_angels
            total_assigned = len(game.players)
            remaining_crewmate_slots = game.max_players - total_assigned - remaining_special_slots
            
            for _ in range(remaining_crewmate_slots):
                available_roles.append('Crewmate')
            
            if not available_roles:
                available_roles = ['Crewmate']
            
            assigned_role = random.choice(available_roles)

            player.assign_role(assigned_role)
            player.assign_tasks()

            if assigned_role == 'Impostor':
                if uid not in game.impostors:
                    game.impostors.append(uid)

            if hasattr(player, 'save'):
                await player.save()
                if hasattr(player, 'save_tasks') and player.db_id:
                    await player.save_tasks()
            
            if hasattr(game, 'db') and hasattr(game.db, 'set_impostors'):
                await game.db.set_impostors(game.channel_id, game.impostors)

            player_count = len(game.players)

            role_emoji = {
                'Impostor': '🔪',
                'Scientist': '🧪',
                'Engineer': '🔧',
                'Guardian Angel': '😇',
                'Crewmate': '👷'
            }.get(assigned_role, '👷')

            role_color = discord.Color.red() if assigned_role == 'Impostor' else discord.Color.blue()

            description_base = (
                f"**Game Code:** `{game.game_code}`\n"
                f"**Players:** {player_count}/{game.max_players}\n\n"
            )

            if assigned_role == 'Impostor':
                description_base += (
                    f"🔪 **Your Mission:** Eliminate the crew without getting caught!\n"
                    f"You have fake tasks to blend in.\n"
                    f"Use `/kill` to eliminate crewmates.\n"
                    f"Use `/sabotage` to create chaos.\n"
                    f"Use `/vent` to quickly move around.\n\n"
                    f"Wait for `/start` to begin!"
                )
            elif assigned_role == 'Scientist':
                description_base += (
                    f"🧪 **Your Mission:** Complete tasks faster than normal crewmates!\n"
                    f"Task completion speed: **1.5x**\n\n"
                    f"Wait for `/start` to begin!"
                )
            elif assigned_role == 'Engineer':
                description_base += (
                    f"🔧 **Your Mission:** Complete tasks and use vents to move quickly!\n"
                    f"You can use vents like impostors.\n"
                    f"Sabotage fix speed: **2x**\n\n"
                    f"Wait for `/start` to begin!"
                )
            elif assigned_role == 'Guardian Angel':
                description_base += (
                    f"😇 **Your Mission:** Complete tasks and protect crewmates!\n"
                    f"You can cast shields on yourself or others.\n"
                    f"Shields: **2 available**\n"
                    f"Use `/shield <player>` to protect someone from kills!\n\n"
                    f"Wait for `/start` to begin!"
                )
            else:
                description_base += (
                    f"👷 **Your Mission:** Complete all your tasks to win!\n"
                    f"Watch out for suspicious behavior.\n\n"
                    f"Wait for `/start` to begin!"
                )

            private_embed = discord.Embed(
                title=f"{role_emoji} You joined as {assigned_role}!",
                description=description_base,
                color=role_color
            )
            
            role_card_buffer = await create_role_reveal_card(
                player_name=player.name,
                role=assigned_role,
                task_count=len(player.tasks),
                avatar_url=avatar_url
            )
            
            role_card_file = discord.File(role_card_buffer, filename="role_card.png")
            private_embed.set_image(url="attachment://role_card.png")

            await interaction.followup.send(
                embed=private_embed,
                file=role_card_file,
                ephemeral=True
            )

            public_embed = discord.Embed(
                title="✅ Player Joined",
                description=f"**{interaction.user.display_name}** joined the lobby!\n\n**Players:** {player_count}/{game.max_players}",
                color=discord.Color.green()
            )

            game_channel = self.bot.get_channel(game_channel_id)
            if game_channel and isinstance(game_channel, discord.TextChannel):
                await game_channel.send(embed=public_embed)
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
