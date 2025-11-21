import discord
from discord import app_commands, ui
from discord.ext import commands
import asyncio
from typing import cast


async def safe_dm_user(user: discord.User | discord.Member, **kwargs):
    try:
        await user.send(**kwargs)
        return True
    except (discord.Forbidden, discord.HTTPException):
        return False


class ShieldView(ui.View):
    def __init__(self, game, guardian, bot):
        super().__init__(timeout=30)
        self.game = game
        self.guardian = guardian
        self.bot = bot

        alive_players = [p for p in game.players.values() if p.alive]
        
        for player in alive_players[:25]:
            button = ui.Button(
                label=player.name[:80], 
                style=discord.ButtonStyle.primary if player.user_id != guardian.user_id else discord.ButtonStyle.success,
                emoji="🛡️"
            )
            button.callback = self._create_shield_callback(player)
            self.add_item(button)

    def _create_shield_callback(self, target):
        async def callback(interaction: discord.Interaction):
            await interaction.response.defer()
            
            if hasattr(target, 'shielded') and target.shielded:
                await interaction.edit_original_response(
                    content=f"❌ **{target.name}** already has an active shield!",
                    view=None
                )
                self.stop()
                return
            
            target.shielded = True
            target.shielded_by = self.guardian.user_id
            self.guardian.shields_remaining -= 1
            self.guardian.shield_cooldown = 60
            
            self_shield = target.user_id == self.guardian.user_id
            
            if self_shield:
                await interaction.edit_original_response(
                    content=f"🛡️ You cast a protective shield around yourself!\n\nYou are now protected from the next impostor attack.\nShields remaining: **{self.guardian.shields_remaining}/2**",
                    view=None
                )
            else:
                await interaction.edit_original_response(
                    content=f"🛡️ You cast a protective shield around **{target.name}**!\n\nThey are now protected from the next impostor attack.\nShields remaining: **{self.guardian.shields_remaining}/2**",
                    view=None
                )
                
                if not target.is_bot:
                    try:
                        guild = interaction.guild
                        if guild:
                            target_user = guild.get_member(target.user_id)
                            if target_user:
                                embed = discord.Embed(
                                    title="🛡️ You Are Protected!",
                                    description=f"A Guardian Angel has cast a protective shield around you!\n\nYou are now protected from the next impostor attack.",
                                    color=discord.Color.gold()
                                )
                                embed.set_footer(text="The shield will break after blocking one attack.")
                                await safe_dm_user(target_user, embed=embed)
                    except Exception as e:
                        print(f"Error notifying shielded player: {e}")
            
            self.stop()

        return callback


class ShieldCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.games = getattr(bot, "amongus_games", {})
        asyncio.create_task(self._cooldown_loop())

    async def cog_load(self):
        print("ShieldCog loaded")

    async def _cooldown_loop(self):
        while True:
            await asyncio.sleep(1)
            for game in self.games.values():
                if game.phase == "tasks":
                    for player in game.players.values():
                        if player.role == "Guardian Angel" and player.shield_cooldown > 0:
                            player.shield_cooldown -= 1

    @app_commands.command(name="shield", description="Cast a protective shield on a player anywhere on the map (Guardian Angels only)")
    async def shield(self, interaction: discord.Interaction):
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

        if player.role != "Guardian Angel":
            await interaction.response.send_message("🚫 Only Guardian Angels can use shields!", ephemeral=True)
            return

        if game.phase != "tasks":
            await interaction.response.send_message(f"Cannot shield during {game.phase}!", ephemeral=True)
            return

        if player.shields_remaining <= 0:
            await interaction.response.send_message(
                "❌ You have no shields remaining!\n"
                f"💡 You had **2 shields** at the start of the game.",
                ephemeral=True,
            )
            return

        if player.shield_cooldown > 0:
            await interaction.response.send_message(
                f"⏳ Shield on cooldown! {player.shield_cooldown}s remaining",
                ephemeral=True,
            )
            return

        alive_players = [p for p in game.players.values() if p.alive]
        if not alive_players:
            await interaction.response.send_message("No alive players to shield!", ephemeral=True)
            return

        view = ShieldView(game, player, self.bot)
        await interaction.response.send_message(
            "🛡️ **Select a player to shield (anywhere on the map):**\n\nThe shield will protect them from the next impostor attack.",
            view=view,
            ephemeral=True
        )

    @app_commands.command(name="shieldstatus", description="Check your shield status")
    async def shieldstatus(self, interaction: discord.Interaction):
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

        if player.role != "Guardian Angel":
            if hasattr(player, 'shielded') and player.shielded:
                shield_guardian = None
                if hasattr(player, 'shielded_by') and player.shielded_by:
                    shield_guardian = game.players.get(player.shielded_by)
                
                guardian_name = shield_guardian.name if shield_guardian else "a Guardian Angel"
                await interaction.response.send_message(
                    f"🛡️ You are currently protected by {guardian_name}'s shield!",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "You don't have any active shields.",
                    ephemeral=True
                )
            return

        embed = discord.Embed(
            title="😇 Guardian Angel Shield Status",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="Shields Remaining",
            value=f"🛡️ **{player.shields_remaining}/2**",
            inline=True
        )
        
        if player.shield_cooldown > 0:
            embed.add_field(
                name="Cooldown",
                value=f"⏳ **{player.shield_cooldown}s**",
                inline=True
            )
        else:
            embed.add_field(
                name="Status",
                value="✅ **Ready**",
                inline=True
            )
        
        shielded_players = [p for p in game.players.values() if hasattr(p, 'shielded') and p.shielded and hasattr(p, 'shielded_by') and p.shielded_by == uid]
        if shielded_players:
            shielded_names = ", ".join([p.name for p in shielded_players])
            embed.add_field(
                name="Active Shields",
                value=f"🛡️ {shielded_names}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ShieldCog(bot))
