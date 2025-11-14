"""Vent system for impostors"""
import discord
from discord import app_commands, ui
from discord.ext import commands
import random
from typing import cast


VENT_LOCATIONS = [
    "Cafeteria", "Electrical", "Security", "MedBay",
    "Nav", "Shields", "Weapons", "Admin",
    "Storage", "Engine", "Reactor"
]


class VentView(ui.View):
    """Interactive vent UI"""
    
    def __init__(self, game, current_location: str, bot, player):
        super().__init__(timeout=30)
        self.game = game
        self.current_location = current_location
        self.bot = bot
        self.player = player
        
        # Add vent destination buttons (random 2-3 connected vents)
        num_destinations = random.randint(2, 3)
        destinations = random.sample([loc for loc in VENT_LOCATIONS if loc != current_location], num_destinations)
        
        for dest in destinations:
            button = ui.Button(label=f"➡️ {dest}", style=discord.ButtonStyle.secondary)
            button.callback = self._create_vent_callback(dest)
            self.add_item(button)
        
        # Add kill button if player is an impostor with no cooldown
        if player.role == "Impostor" and player.kill_cooldown == 0:
            kill_button = ui.Button(label="🔪 Kill from Vent", style=discord.ButtonStyle.danger, emoji="🌀")
            kill_button.callback = self._kill_from_vent
            self.add_item(kill_button)
            
        # Add exit vent button
        exit_button = ui.Button(label="🚪 Exit Vent", style=discord.ButtonStyle.primary)
        exit_button.callback = self._exit_vent
        self.add_item(exit_button)
        
    def _create_vent_callback(self, destination: str):
        async def callback(interaction: discord.Interaction):
            uid = interaction.user.id
            if uid in self.game.players:
                player = self.game.players[uid]
                player.location = destination
                player.in_vent = False
                

            await interaction.response.edit_message(
                content=f"🌀 You traveled through the vents to **{destination}**!",
                view=None
            )
            self.stop()
        return callback
        
    async def _exit_vent(self, interaction: discord.Interaction):
        uid = interaction.user.id
        if uid in self.game.players:
            player = self.game.players[uid]
            player.in_vent = False
            
            # Very low chance (5%) of visual indicator when exiting vent
            if random.random() < 0.05 and isinstance(interaction.channel, discord.TextChannel):
                try:
                    await interaction.channel.send(
                        f"👀 Someone exited the vents in **{self.current_location}**..."
                    )
                except Exception:
                    pass
            
        await interaction.response.edit_message(
            content=f"🚪 You exited the vent at **{self.current_location}**.",
            view=None
        )
        self.stop()
    
    async def _kill_from_vent(self, interaction: discord.Interaction):
        """Kill a nearby player from the vent"""
        # Get alive crewmates
        alive_crewmates = self.game.alive_crewmates()
        
        if not alive_crewmates:
            await interaction.response.send_message(
                "❌ No targets available!",
                ephemeral=True
            )
            return
        
        # Limit to 2-3 random targets (low range from vent)
        if len(alive_crewmates) > 3:
            targets = random.sample(alive_crewmates, random.randint(2, 3))
        else:
            targets = alive_crewmates
        
        # Create kill selection view
        from .game_kill import KillView
        
        # Close current vent view
        await interaction.response.edit_message(
            content="🌀🔪 **Select your target (limited range from vent):**",
            view=None
        )
        
        # Send kill view
        kill_view = KillView(self.game, self.player, self.bot, from_vent=True)
        await interaction.followup.send(
            "🔪 **Choose your victim:**",
            view=kill_view,
            ephemeral=True
        )
        
        self.stop()


class VentCog(commands.Cog):
    """Vent system for impostors"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.games = getattr(bot, 'amongus_games', {})
        
    async def cog_load(self):
        print('VentCog loaded')
        
    @app_commands.command(name='vent', description='Enter a vent (Impostors and Engineers only)')
    async def vent(self, interaction: discord.Interaction):
        if not interaction.channel:
            await interaction.response.send_message('Use in a server channel.', ephemeral=True)
            return
            
        ch_id = interaction.channel.id
        if ch_id not in self.games:
            await interaction.response.send_message('No active game.', ephemeral=True)
            return
            
        game = self.games[ch_id]
        uid = interaction.user.id
        
        if uid not in game.players:
            await interaction.response.send_message('Not in game.', ephemeral=True)
            return
            
        player = game.players[uid]
        
        if not player.alive:
            await interaction.response.send_message('💀 You are dead!', ephemeral=True)
            return
            
        if not player.can_vent:
            await interaction.response.send_message(
                '🚫 Only Impostors and Engineers can use vents!', 
                ephemeral=True
            )
            return
            
        if game.phase != 'tasks':
            await interaction.response.send_message(f'Cannot vent during {game.phase}!', ephemeral=True)
            return

        current_room = game.get_room(player.location)
        if not current_room or not current_room.can_vent:
            await interaction.response.send_message(
                f'❌ There are no vents in **{player.location}**!',
                ephemeral=True
            )
            return
            
        player.in_vent = True
        
        # Very low chance (5%) of visual indicator when entering vent
        if random.random() < 0.05 and isinstance(interaction.channel, discord.TextChannel):
            try:
                await interaction.channel.send(
                    f"👀 Someone noticed movement near the vents in **{player.location}**..."
                )
            except Exception:
                pass
        
        view = VentView(game, player.location, self.bot, player)
        await interaction.response.send_message(
            f"🌀 **You entered the vent at {player.location}!**\n"
            f"Select a destination or exit the vent:",
            view=view,
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(VentCog(bot))
