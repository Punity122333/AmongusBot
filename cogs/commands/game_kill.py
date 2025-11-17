import discord
from discord import app_commands, ui
from discord.ext import commands
import asyncio
import random
from typing import cast
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


class KillView(ui.View):
    def __init__(self, game, killer, bot, from_vent=False):
        super().__init__(timeout=30)
        self.game = game
        self.killer = killer
        self.bot = bot
        self.from_vent = from_vent

        alive_crewmates = [p for p in game.alive_crewmates() if not p.is_bot or True]
        
        if not from_vent:
            current_room = game.get_room(killer.location)
            connected_rooms = [killer.location]
            if current_room and current_room.connected_rooms:
                connected_rooms.extend(current_room.connected_rooms)
            alive_crewmates = [p for p in alive_crewmates if p.location in connected_rooms]
        
        if from_vent and len(alive_crewmates) > 3:
            alive_crewmates = random.sample(alive_crewmates, random.randint(2, 3))

        for crewmate in alive_crewmates[:10]:
            button = ui.Button(
                label=crewmate.name[:80], style=discord.ButtonStyle.danger, emoji="🔪"
            )
            button.callback = self._create_kill_callback(crewmate)
            self.add_item(button)

    def _create_kill_callback(self, target):
        async def callback(interaction: discord.Interaction):
            await interaction.response.defer()
            
            target.alive = False
            self.killer.kill_cooldown = self.game.kill_cooldown

            self.game.add_body_to_room(self.killer.location, target.name)

            witnesses = [
                p for p in self.game.players.values() 
                if p.alive 
                and p.user_id != self.killer.user_id 
                and p.user_id != target.user_id 
                and p.location == self.killer.location
                and not p.is_bot
            ]

            if interaction.channel and isinstance(interaction.channel, discord.TextChannel):
                try:
                    await interaction.channel.send(
                        f"💀 **Someone has been killed!** The crew is down to {len(self.game.alive_players())} players..."
                    )
                except Exception as e:
                    print(f"Error sending kill message: {e}")

                if witnesses:
                    for witness in witnesses:
                        try:
                            witness_user = interaction.guild.get_member(witness.user_id) if interaction.guild else None
                            if witness_user:
                                embed = discord.Embed(
                                    title="👁️ YOU WITNESSED A MURDER!",
                                    description=f"**YOU SAW {self.killer.name.upper()} KILL {target.name.upper()} IN {self.killer.location.upper()}!**\n\nYou can report this immediately!",
                                    color=discord.Color.red()
                                )
                                embed.add_field(
                                    name="🔍 What You Saw",
                                    value=f"**Killer:** {self.killer.name}\n**Victim:** {target.name}\n**Location:** {self.killer.location}",
                                    inline=False
                                )
                                embed.set_footer(text="Use /reportbody to call a meeting!")
                                await safe_dm_user(witness_user, embed=embed)
                        except Exception as e:
                            print(f"Error DMing witness: {e}")

                if not target.is_bot and interaction.guild:
                    try:
                        from amongus.card_generator import create_death_card
                        
                        victim_user = interaction.guild.get_member(target.user_id)
                        if victim_user:
                            card_buffer = await create_death_card(target.name, target.avatar_url)
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

                try:
                    killer_user = None
                    if interaction.guild:
                        killer_user = interaction.guild.get_member(self.killer.user_id)
                    if killer_user:
                        from .game_bodies import BodyDiscoveryView
                        
                        embed = discord.Embed(
                            title="💀 Body Discovered!",
                            description=f"You stumbled upon **{target.name}'s** lifeless body lying on the ground in **{self.killer.location}**...\n\n**Choose your action:**",
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
                        embed.set_footer(text="⏰ You have 60 seconds to decide")
                        
                        view = BodyDiscoveryView(self.bot, self.game, interaction.channel, target, self.killer.name, self.killer.location)
                        
                        await safe_dm_user(killer_user, embed=embed, view=view)
                except Exception as e:
                    print(f"Error sending impostor body discovery: {e}")

                try:
                    from .game_bodies import notify_body_discovery
                    
                    if self.from_vent:
                        if random.random() < 0.20:
                            await notify_body_discovery(
                                self.bot,
                                self.game,
                                interaction.channel,
                                target,
                                self.killer.name,
                            )
                    else:
                        await notify_body_discovery(
                            self.bot,
                            self.game,
                            interaction.channel,
                            target,
                            self.killer.name,
                        )
                except Exception as e:
                    print(f"Error in kill notification: {e}")

            await interaction.edit_original_response(
                content=f"🔪 You killed **{target.name}**!\nKill cooldown: {self.game.kill_cooldown}s",
                view=None,
            )
            self.stop()

            if interaction.channel and isinstance(interaction.channel, discord.TextChannel):
                await check_and_announce_winner(self.game, interaction.channel, "kill", self.bot)

        return callback


class KillCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.games = getattr(bot, "amongus_games", {})
        asyncio.create_task(self._cooldown_loop())

    async def cog_load(self):
        print("KillCog loaded")

    async def _cooldown_loop(self):
        while True:
            await asyncio.sleep(1)
            for game in self.games.values():
                if game.phase == "tasks":
                    for player in game.players.values():
                        if player.role == "Impostor" and player.kill_cooldown > 0:
                            player.kill_cooldown -= 1

    @app_commands.command(name="kill", description="Kill a nearby player (Impostors only)")
    async def kill(self, interaction: discord.Interaction):
        if not interaction.channel or not interaction.guild:
            await interaction.response.send_message("Use in a server channel.", ephemeral=True)
            return

        ch_id = interaction.channel.id
        if ch_id not in self.games:
            await interaction.response.send_message("No active game.", ephemeral=True)
            return

        game = self.games[ch_id]
        uid = interaction.user.id

        if uid not in game.players:
            await interaction.response.send_message("Not in game.", ephemeral=True)
            return

        player = game.players[uid]

        if not player.alive:
            await interaction.response.send_message("💀 You are dead!", ephemeral=True)
            return

        if player.role != "Impostor":
            await interaction.response.send_message("🚫 Only impostors can kill!", ephemeral=True)
            return

        if game.phase != "tasks":
            await interaction.response.send_message(f"Cannot kill during {game.phase}!", ephemeral=True)
            return

        if player.kill_cooldown > 0:
            await interaction.response.send_message(
                f"⏳ Kill on cooldown! {player.kill_cooldown}s remaining",
                ephemeral=True,
            )
            return

        alive_crewmates = game.alive_crewmates()
        if not alive_crewmates:
            await interaction.response.send_message("No alive crewmates to kill!", ephemeral=True)
            return

        from_vent = player.in_vent
        if from_vent and interaction.channel and isinstance(interaction.channel, discord.TextChannel):
            if random.random() < 0.05:
                try:
                    await interaction.channel.send(
                        f"👀 Someone noticed movement near the vents in **{player.location}**..."
                    )
                except Exception:
                    pass
        
        view = KillView(game, player, self.bot, from_vent=from_vent)
        kill_message = "🔪 **Select your target:**"
        if from_vent:
            kill_message = "🔪 **Select your target (limited range from vent):**"
        
        await interaction.response.send_message(kill_message, view=view, ephemeral=True)

    @app_commands.command(name="killcooldown", description="Check your kill cooldown")
    async def killcooldown(self, interaction: discord.Interaction):
        if not interaction.channel:
            await interaction.response.send_message("Use in a server channel.", ephemeral=True)
            return

        ch_id = interaction.channel.id
        if ch_id not in self.games:
            await interaction.response.send_message("No active game.", ephemeral=True)
            return

        game = self.games[ch_id]
        uid = interaction.user.id

        if uid not in game.players:
            await interaction.response.send_message("Not in game.", ephemeral=True)
            return

        player = game.players[uid]

        if player.role != "Impostor":
            await interaction.response.send_message("Only impostors have kill cooldown!", ephemeral=True)
            return

        if player.kill_cooldown > 0:
            await interaction.response.send_message(
                f"⏳ Kill cooldown: **{player.kill_cooldown}s**", ephemeral=True
            )
        else:
            await interaction.response.send_message("✅ Kill is ready!", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(KillCog(bot))
