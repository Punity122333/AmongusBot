"""Body discovery notifications"""
import time
import discord
from discord import ui, app_commands
from discord.ext import commands
import random
import asyncio
from typing import Optional
from .game_meeting import trigger_meeting
from amongus.card_generator import create_emergency_meeting_card


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


async def teleport_and_report_body(
    bot: discord.Client,
    game,
    channel: discord.TextChannel,
    victim,
    body_location: str
):
    await asyncio.sleep(random.uniform(3, 8))
    
    if game.phase != 'tasks':
        return
    
    alive_non_impostors = [
        p for p in game.alive_players()
        if p.role != "Impostor" and p.user_id != victim.user_id
    ]
    
    if not alive_non_impostors:
        return
    
    reporter = random.choice(alive_non_impostors)
    
    old_location = reporter.location
    reporter.location = body_location
    
    try:
        nearby_players = _get_nearby_players(game, victim, reporter)
        
        game.nearby_players_last_meeting = nearby_players
        
        await channel.send(
            f"🚨 **{reporter.name}** rushed to **{body_location}** and discovered **{victim.name}'s** body, calling an emergency meeting!"
        )
        
        if nearby_players:
            players_list = ", ".join([f"**{p}**" for p in nearby_players])
            await channel.send(
                f"🗣️ **{reporter.name}** says: \"I saw {players_list} near the body!\""
            )
        else:
            await channel.send(
                f"🗣️ **{reporter.name}** says: \"I got here quickly and found the body!\""
            )
        
        await trigger_meeting(game, channel, f"{reporter.name} (found body)", bot)
    except Exception as e:
        print(f"Error in teleport_and_report_body: {e}")


async def schedule_teleport_and_report(
    bot: discord.Client,
    game,
    channel: discord.TextChannel,
    victim,
    body_location: str,
    impostor_view
):
    await asyncio.sleep(random.uniform(8, 15))
    
    if impostor_view.responded:
        return
    
    if game.phase != 'tasks':
        return
    
    alive_non_impostors = [
        p for p in game.alive_players()
        if p.role != "Impostor" and p.user_id != victim.user_id
    ]
    
    if not alive_non_impostors:
        return
    
    reporter = random.choice(alive_non_impostors)
    
    old_location = reporter.location
    reporter.location = body_location
    
    try:
        nearby_players = _get_nearby_players(game, victim, reporter)
        
        game.nearby_players_last_meeting = nearby_players
        
        await channel.send(
            f"🚨 **{reporter.name}** rushed to **{body_location}** and discovered **{victim.name}'s** body, calling an emergency meeting!"
        )
        
        if nearby_players:
            players_list = ", ".join([f"**{p}**" for p in nearby_players])
            await channel.send(
                f"🗣️ **{reporter.name}** says: \"I saw {players_list} near the body!\""
            )
        else:
            await channel.send(
                f"🗣️ **{reporter.name}** says: \"I got here quickly and found the body!\""
            )
        
        await trigger_meeting(game, channel, f"{reporter.name} (found body)", bot)
    except Exception as e:
        print(f"Error in schedule_teleport_and_report: {e}")


class BodyDiscoveryView(ui.View):
    """Interactive body discovery options"""
    
    def __init__(self, bot: discord.Client, game, channel: discord.TextChannel, victim, discoverer_name: str, location: str):
        super().__init__(timeout=60)
        self.bot = bot
        self.game = game
        self.channel = channel
        self.victim = victim
        self.discoverer_name = discoverer_name
        self.location = location
        self.responded = False
        
    @ui.button(label="📢 Call Meeting", style=discord.ButtonStyle.danger)
    async def call_meeting(self, interaction: discord.Interaction, button: ui.Button):
        if self.responded:
            await interaction.response.send_message("You already responded!", ephemeral=True)
            return
        
        if self.game.phase == "meeting":
            await interaction.response.send_message("❌ A meeting has already been called!", ephemeral=True)
            return
            
        self.responded = True

        for item in self.children:
            if isinstance(item, ui.Button):
                item.disabled = True
        
        embed = discord.Embed(
            title="📢 Meeting Called!",
            description=f"You reported **{self.victim.name}'s** body in **{self.location}** and called an emergency meeting!",
            color=discord.Color.red()
        )
        embed.set_footer(text="The crew will now discuss who the impostor might be.")
        
        try:
            await interaction.response.edit_message(
                embed=embed,
                view=self
            )
        except discord.errors.NotFound:
            await interaction.response.send_message("❌ Meeting already called by someone else!", ephemeral=True)
            return
        
        nearby_players = _get_nearby_players(self.game, self.victim, self.game.players.get(interaction.user.id))
        
        self.game.nearby_players_last_meeting = nearby_players
        
        await self.channel.send(
            f"👁️ **{self.discoverer_name}** discovered **{self.victim.name}'s** body and called a meeting!"
        )
        
        if nearby_players:
            players_list = ", ".join([f"**{p}**" for p in nearby_players])
            await self.channel.send(
                f"🗣️ **{self.discoverer_name}** says: \"I saw {players_list} near the body!\""
            )
        else:
            await self.channel.send(
                f"🗣️ **{self.discoverer_name}** says: \"The area seemed empty when I found the body.\""
            )

        
        await trigger_meeting(self.game, self.channel, f"{self.discoverer_name} (found body)", self.bot)
        
        self.stop()
    
    @ui.button(label="🤫 Ignore", style=discord.ButtonStyle.secondary)
    async def ignore_body(self, interaction: discord.Interaction, button: ui.Button):
        if self.responded:
            await interaction.response.send_message("You already responded!", ephemeral=True)
            return
            
        self.responded = True

        for item in self.children:
            if isinstance(item, ui.Button):
                item.disabled = True
        
        embed = discord.Embed(
            title="🤫 Ignored",
            description=f"You decided to ignore **{self.victim.name}'s** body and walk away quietly...\n\nThe impostor might still be nearby.",
            color=discord.Color.dark_grey()
        )
        embed.set_footer(text="No one else will know you saw the body.")
        
        await interaction.response.edit_message(
            embed=embed,
            view=self
        )
        
        self.stop()
    
    @ui.button(label="🔍 Investigate", style=discord.ButtonStyle.primary)
    async def investigate(self, interaction: discord.Interaction, button: ui.Button):
        alive_players = self.game.alive_players()
        
        impostors = [p for p in self.game.players.values() if p.role == "Impostor" and p.alive]
        
        nearby_players = []
        
        num_nearby = min(random.randint(2, 4), len(alive_players))
        potential_nearby = random.sample(alive_players, num_nearby)
        
        impostor_included = False
        for impostor in impostors:
            if random.random() < 0.80:
                if impostor not in potential_nearby:
                    if potential_nearby:
                        potential_nearby[random.randint(0, len(potential_nearby) - 1)] = impostor
                impostor_included = True
                break
        
        nearby_players = [p.name for p in potential_nearby if p.user_id != self.victim.user_id]
        
        random.shuffle(nearby_players)
        
        embed = discord.Embed(
            title="🔍 Investigation Results",
            description=f"You investigated the area around **{self.victim.name}'s** body in **{self.location}**...",
            color=discord.Color.dark_blue()
        )
        
        if nearby_players:
            players_list = "\n".join([f"• {name}" for name in nearby_players])
            embed.add_field(
                name="Players Spotted Nearby:",
                value=players_list,
                inline=False
            )
        else:
            embed.add_field(
                name="Players Spotted Nearby:",
                value="*The area seems empty...*",
                inline=False
            )
        
        embed.set_footer(text="This list may not include everyone who was actually nearby.")
        
        await interaction.response.send_message(
            content="🔍 You investigated the scene!",
            embed=embed,
            ephemeral=True
        )



async def notify_body_discovery(
    bot: discord.Client,
    game,
    channel: discord.TextChannel,
    victim,
    room_name: str,
    discoverer_id: Optional[int] = None,
):
    """Notify players about a body being discovered"""
    
    if discoverer_id:
        discoverer = game.players.get(discoverer_id)
        if discoverer and not discoverer.is_bot:
            try:
                guild = bot.get_guild(game.guild_id) if hasattr(bot, 'get_guild') else None
                if guild:
                    user = guild.get_member(discoverer.user_id)
                    if user:
                        
                        
                        embed = discord.Embed(
                            title="💀 Body Discovered!",
                            description=f"You stumbled upon **{victim.name}'s** lifeless body lying on the ground in **{room_name}**...\n\n**Choose your action:**",
                            color=discord.Color.dark_red()
                        )
                        embed.add_field(
                            name="📢 Call Meeting",
                            value="Report the body and gather everyone to discuss",
                            inline=False
                        )
                        embed.add_field(
                            name="🤫 Ignore",
                            value="Walk away quietly and pretend you didn't see anything",
                            inline=False
                        )
                        embed.add_field(
                            name="🔍 Investigate",
                            value="Look around to see who was nearby (may help find the impostor)",
                            inline=False
                        )
                        
                        view = BodyDiscoveryView(bot, game, channel, victim, discoverer.name, room_name)
                        await safe_dm_user(user, embed=embed, view=view)
            except Exception as e:
                print(f"Error sending body discovery DM to player: {e}")
        return

    if random.random() < 0.6: 
        
        alive_bots = [p for p in game.alive_players() if p.user_id != victim.user_id and p.is_bot]
        
        if alive_bots:
            discoverer = random.choice(alive_bots)
            
            await asyncio.sleep(5)
            
            if game.phase != 'tasks':
                return
            
            try:
                nearby_players = _get_nearby_players(game, victim, discoverer)
                
                game.nearby_players_last_meeting = nearby_players
                
                await channel.send(
                    f"👁️ **{discoverer.name}** discovered **{victim.name}'s** body and called a meeting!"
                )
                
                if nearby_players:
                    players_list = ", ".join([f"**{p}**" for p in nearby_players])
                    await channel.send(
                        f"🗣️ **{discoverer.name}** says: \"I saw {players_list} near the body!\""
                    )
                else:
                    await channel.send(
                        f"🗣️ **{discoverer.name}** says: \"The area seemed empty when I found the body.\""
                    )
                
                
                await trigger_meeting(game, channel, f"{discoverer.name} (found body)", bot)
            except Exception as e:
                print(f"Error in bot body discovery: {e}")


def _get_nearby_players(game, victim, discoverer) -> list[str]:
    """Get list of players that were 'nearby' the body when discovered"""
    alive_players = game.alive_players()
    
    # Get impostors
    impostors = [p for p in game.players.values() if p.role == "Impostor" and p.alive]
    
    # Build nearby players list (2-4 players)
    num_nearby = min(random.randint(2, 4), len(alive_players))
    if num_nearby == 0:
        return []
    
    potential_nearby = random.sample(alive_players, num_nearby)
    
    impostor_included = False
    for impostor in impostors:
        if random.random() < 0.70:  # 70% chance to include impostor
            if impostor not in potential_nearby:
                # Replace a random player with the impostor
                if potential_nearby:
                    potential_nearby[random.randint(0, len(potential_nearby) - 1)] = impostor
            impostor_included = True
            break
    
    nearby_players = [p.name for p in potential_nearby 
                     if p.user_id != victim.user_id and p.user_id != discoverer.user_id]
    
    random.shuffle(nearby_players)
    
    return nearby_players


class BodyReportCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.games = getattr(bot, "amongus_games", {})

    async def cog_load(self):
        pass

    @app_commands.command(name='reportbody', description='Report a body and call an emergency meeting')
    async def reportbody(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        ch_id = interaction.channel_id
        uid = interaction.user.id
        
        if ch_id not in self.games:
            await interaction.followup.send("❌ No active game in this channel!", ephemeral=True)
            return
        
        game = self.games[ch_id]
        
        if game.phase != 'tasks':
            await interaction.followup.send("❌ You can only report bodies during the task phase!", ephemeral=True)
            return
        
        if uid not in game.players:
            await interaction.followup.send("❌ You are not in this game!", ephemeral=True)
            return
        
        player = game.players[uid]
        
        if not player.alive:
            await interaction.followup.send("❌ Ghosts cannot report bodies!", ephemeral=True)
            return

        
        time_since_start = time.time() - game.game_start_time
        if time_since_start < 100:
            remaining = int(100 - time_since_start)
            await interaction.followup.send(
                f"⏳ Cannot report bodies yet! Wait {remaining}s after game start to call meetings.",
                ephemeral=True
            )
            return
        
        current_room_obj = game.get_room(player.location)
        
        if not current_room_obj or not current_room_obj.bodies:
            await interaction.followup.send(
                f"❌ There are no bodies in **{player.location}**!",
                ephemeral=True
            )
            return
        
        if isinstance(interaction.channel, discord.TextChannel):
            game.phase = 'meeting'
            
            body_names = ", ".join(current_room_obj.bodies)
            
           
            
            card_buffer = await create_emergency_meeting_card()
            file = discord.File(card_buffer, filename="meeting.png")
            
            embed = discord.Embed(
                title="🚨 BODY REPORTED! 🚨",
                description=f"**{player.name}** discovered {body_names}'s body in **{player.location}**!",
                color=discord.Color.red()
            )
            embed.set_image(url="attachment://meeting.png")
            embed.add_field(
                name="Meeting Started",
                value="Discuss who you think the impostor is and vote using `/vote <player_name>`",
                inline=False
            )
            
            await interaction.channel.send(embed=embed, file=file)
            await interaction.followup.send("✅ You reported the body and called a meeting!", ephemeral=True)

async def setup(bot: commands.Bot):
    """Classic (synchronous) setup for extension loader compatibility."""
    await bot.add_cog(BodyReportCog(bot))
