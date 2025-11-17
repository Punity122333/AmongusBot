"""Meeting and voting commands"""

import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import random
from amongus.core import AmongUsGame
from amongus.card_generator import (
    create_emergency_meeting_card,
    create_vote_result_card,
)
from .game_utils import check_and_announce_winner
from typing import cast, Optional


def validate_player_in_game(
    interaction: discord.Interaction, games: dict, alive_required: bool = True
):
    """Validate player is in game and alive. Returns (game, player) or (None, error_msg)"""
    ch_id = interaction.channel.id if interaction.channel else None
    if not ch_id or ch_id not in games:
        return None, "No active game in this channel."

    game = games[ch_id]
    uid = interaction.user.id

    if uid not in game.players:
        return None, "You are not in this game."

    if alive_required and not game.players[uid].alive:
        return None, "💀 You are dead!"

    return game, game.players[uid]


class MeetingCog(commands.Cog):
    """Commands for meetings and voting"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.games = getattr(bot, "amongus_games", {})
        
        asyncio.create_task(self._meeting_cooldown_loop())

    async def cog_load(self):
        print("MeetingCog loaded")
    
    async def _meeting_cooldown_loop(self):
        """Reduce meeting cooldowns every second"""
        try:
            while True:
                await asyncio.sleep(1)
                for game in list(self.games.values()):  # Use list() to avoid dict change during iteration
                    if game.phase == "tasks" and game.meeting_cooldown > 0:
                        game.meeting_cooldown -= 1
        except asyncio.CancelledError:
            # Task cancelled, exit gracefully
            pass

    @app_commands.command(name="meeting", description="Call an emergency meeting")
    async def emergency_meeting(self, interaction: discord.Interaction):
        if not interaction.channel or not interaction.guild:
            await interaction.response.send_message(
                "Use in a server channel.", ephemeral=True
            )
            return

        result = validate_player_in_game(interaction, self.games, alive_required=True)
        if result[0] is None:
            await interaction.response.send_message(result[1], ephemeral=True)
            return

        game, player = result

        if game.phase != "tasks":
            await interaction.response.send_message(
                f"Cannot call meeting during {game.phase}!", ephemeral=True
            )
            return

        # Check global meeting cooldown
        if game.meeting_cooldown > 0:
            await interaction.response.send_message(
                f"⏳ Emergency meeting on cooldown! {game.meeting_cooldown}s remaining",
                ephemeral=True
            )
            return

        import time
        time_since_start = time.time() - game.game_start_time
        if time_since_start < 100:
            remaining = int(100 - time_since_start)
            await interaction.response.send_message(
                f"⏳ Cannot call meetings yet! Wait {remaining}s after game start.",
                ephemeral=True
            )
            return

        # Check emergency meeting limit
        if player.emergency_meetings_left <= 0:
            await interaction.response.send_message(
                "❌ You have no emergency meetings left!", ephemeral=True
            )
            return

        # Deduct emergency meeting
        player.emergency_meetings_left -= 1

        await interaction.response.defer()
        await trigger_meeting(
            game, cast(discord.TextChannel, interaction.channel), player.name, self.bot
        )

    @app_commands.command(name="vote", description="Vote for a player")
    @app_commands.describe(player_name="Name of the player to vote for")
    async def vote(self, interaction: discord.Interaction, player_name: str):
        result = validate_player_in_game(interaction, self.games, alive_required=True)
        if result[0] is None:
            await interaction.response.send_message(result[1], ephemeral=True)
            return

        game, player = result

        if game.phase != "meeting":
            await interaction.response.send_message("Not in a meeting!", ephemeral=True)
            return

        # Find target
        target = next(
            (
                p
                for p in game.players.values()
                if p.name.lower() == player_name.lower() and p.alive
            ),
            None,
        )

        if not target:
            await interaction.response.send_message(
                f'Player "{player_name}" not found.', ephemeral=True
            )
            return

        await game.cast_vote(interaction.user.id, target.user_id)
        await interaction.response.send_message(
            f"🗳️ Voted for **{target.name}**", ephemeral=True
        )

    @app_commands.command(name="skip", description="Skip voting")
    async def skip(self, interaction: discord.Interaction):
        result = validate_player_in_game(interaction, self.games, alive_required=True)
        if result[0] is None:
            await interaction.response.send_message(result[1], ephemeral=True)
            return

        game, player = result

        if game.phase != "meeting":
            await interaction.response.send_message("Not in a meeting!", ephemeral=True)
            return

        await game.cast_vote(interaction.user.id, -1)
        await interaction.response.send_message("🤷 Voted to skip", ephemeral=True)

    @app_commands.command(name="meetingstatus", description="Check emergency meeting availability")
    async def meeting_status(self, interaction: discord.Interaction):
        result = validate_player_in_game(interaction, self.games, alive_required=False)
        if result[0] is None:
            await interaction.response.send_message(result[1], ephemeral=True)
            return

        game, player = result

        embed = discord.Embed(
            title="⚠️ Emergency Meeting Status",
            color=discord.Color.gold()
        )
        
        # Player's meetings left
        meetings_left = player.emergency_meetings_left
        embed.add_field(
            name="Your Meetings Left",
            value=f"{'🟢' if meetings_left > 0 else '🔴'} {meetings_left}/1",
            inline=True
        )
        
        # Global cooldown
        global_cd = game.meeting_cooldown
        cd_status = f"✅ Ready" if global_cd == 0 else f"⏳ {global_cd}s"
        embed.add_field(
            name="Global Cooldown",
            value=cd_status,
            inline=True
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def _bot_voting_behavior(game: AmongUsGame, channel: discord.TextChannel):
    """Make bots vote intelligently during meetings"""
    await asyncio.sleep(random.uniform(5, 15))
    
    if game.phase == "ended":
        return
    
    alive_bots = [p for p in game.players.values() if p.is_bot and p.alive]
    alive_players = game.alive_players()
    
    for bot in alive_bots:
        await asyncio.sleep(random.uniform(2, 8))
        
        if game.phase != "meeting" or game.phase == "ended":
            return
        
        if bot.role == "Impostor":
            crewmates = [p for p in alive_players if p.role != "Impostor" and p.user_id != bot.user_id]
            
            nearby_names = game.nearby_players_last_meeting if hasattr(game, 'nearby_players_last_meeting') else []
            nearby_crewmates = [p for p in crewmates if p.name in nearby_names]
            
            if nearby_crewmates and random.random() < 0.65:
                target = random.choice(nearby_crewmates)
                await game.cast_vote(bot.user_id, target.user_id)
                try:
                    await channel.send(f"🗳️ **{bot.name}** voted for **{target.name}**.")
                except:
                    pass
            elif random.random() < 0.4:
                await game.cast_vote(bot.user_id, -1)
                try:
                    await channel.send(f"🤷 **{bot.name}** voted to skip.")
                except:
                    pass
            elif crewmates:
                target = random.choice(crewmates)
                await game.cast_vote(bot.user_id, target.user_id)
                try:
                    await channel.send(f"🗳️ **{bot.name}** voted for **{target.name}**.")
                except:
                    pass
        else:
            other_players = [p for p in alive_players if p.user_id != bot.user_id]
            
            nearby_names = game.nearby_players_last_meeting if hasattr(game, 'nearby_players_last_meeting') else []
            nearby_targets = [p for p in other_players if p.name in nearby_names]
            far_targets = [p for p in other_players if p.name not in nearby_names]
            
            if nearby_targets and random.random() < 0.75:
                weights = [2.7 if p in nearby_targets else 0.5 for p in other_players]
                target = random.choices(other_players, weights=weights, k=1)[0]
                await game.cast_vote(bot.user_id, target.user_id)
                try:
                    await channel.send(f"🗳️ **{bot.name}** voted for **{target.name}**.")
                except:
                    pass
            elif random.random() < 0.35:
                await game.cast_vote(bot.user_id, -1)
                try:
                    await channel.send(f"🤷 **{bot.name}** voted to skip.")
                except:
                    pass
            elif other_players:
                target = random.choice(other_players)
                await game.cast_vote(bot.user_id, target.user_id)
                try:
                    await channel.send(f"🗳️ **{bot.name}** voted for **{target.name}**.")
                except:
                    pass


async def trigger_meeting(
    game: AmongUsGame, channel: discord.TextChannel, caller_name: Optional[str] = None, bot=None
):
    """Trigger an emergency meeting"""
    if game.phase == "meeting":
        return

    game.phase = "meeting"
    await game.clear_votes()

    # Create meeting card
    card_buffer = await create_emergency_meeting_card(caller_name)
    file = discord.File(card_buffer, filename="meeting.png")

    embed = discord.Embed(
        title="⚠️ EMERGENCY MEETING ⚠️",
        description=(
            f"Called by: **{caller_name}**\n\n"
            f"Discuss and vote who you think is suspicious!\n\n"
            f"Use `/vote <player_name>` to vote\n"
            f"Use `/skip` to skip voting\n\n"
            f"**The player with the most votes will be ejected!**\n"
            f"⏱Voting closes in 5 minutes or when everyone votes"
        ),
        color=discord.Color.red(),
    )
    embed.set_image(url="attachment://meeting.png")

    await channel.send(embed=embed, file=file)

    # Bots vote with AI behavior
    asyncio.create_task(_bot_voting_behavior(game, channel))

    # Wait for votes - check every 2 seconds if everyone voted, or 300s timeout
    elapsed = 0
    max_time = 300  # 5 minutes
    check_interval = 2
    
    while elapsed < max_time:
        await asyncio.sleep(check_interval)
        elapsed += check_interval
        
        # Check if game ended (interrupted by win condition)
        if game.phase == "ended":
            return  # Meeting cancelled, game ended
        
        # Check if everyone has voted
        alive_players = game.alive_players()
        votes_cast = len(game.votes)
        
        if votes_cast >= len(alive_players):
            # Everyone has voted, end early
            await channel.send(f"✅ All players have voted! Ending meeting early...")
            break
    
    # Check again if game ended before tallying
    if game.phase == "ended":
        return
    
    if elapsed >= max_time:
        await channel.send("⏰ Time's up! Tallying votes...")

    # Tally votes
    voted_player_id = await game.tally_votes()

    if voted_player_id is None or voted_player_id not in game.players:
        await channel.send("🤷 **No one was ejected.** (Tie or skipped)")
    else:
        voted_player = game.players[voted_player_id]
        vote_count = sum(1 for v in game.votes.values() if v == voted_player_id)

        # Create ejection card
        card_buffer = await create_vote_result_card(
            voted_player.name, vote_count, voted_player.role == "Impostor"
        )
        file = discord.File(card_buffer, filename="ejection.png")

        # Eject player
        voted_player.alive = False

        embed = discord.Embed(
            title="🚀 Ejection",
            color=(
                discord.Color.red()
                if voted_player.role == "Impostor"
                else discord.Color.blue()
            ),
        )
        embed.set_image(url="attachment://ejection.png")

        await channel.send(embed=embed, file=file)

    if not await check_and_announce_winner(game, channel, "meeting", bot):
        game.phase = "tasks"
        game.meeting_cooldown = 60
        game.nearby_players_last_meeting = []
        
        for player in game.players.values():
            if player.role == "Impostor" and player.alive:
                player.kill_cooldown = 40
                player.sabotage_cooldown = 40
        
        await channel.send("🔧 Back to tasks!")


async def setup(bot: commands.Bot):
    await bot.add_cog(MeetingCog(bot))
