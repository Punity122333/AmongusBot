"""Vent system for impostors"""
import discord
from discord import app_commands, ui
from discord.ext import commands
import random
from typing import cast
from amongus.map_renderer import create_vent_map_image


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
        
        # Get valid vent connections from the map layout's vent network
        # Import here to avoid circular import
        from amongus.map_renderer import VentMapRenderer
        temp_renderer = VentMapRenderer(game.map_layout)
        valid_destinations = temp_renderer.vent_connections.get(current_location, [])
        
        # Only show destinations that actually have vents
        destinations = [dest for dest in valid_destinations if game.get_room(dest) and game.get_room(dest).can_vent]
        
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
    
    @app_commands.command(name='ventmap', description='View the vent system map')
    async def ventmap(self, interaction: discord.Interaction):
        """Show a map of all vent locations and connections"""
        await interaction.response.defer(ephemeral=True)
        
        if not interaction.channel:
            await interaction.followup.send('Use in a server channel.', ephemeral=True)
            return
            
        ch_id = interaction.channel.id
        if ch_id not in self.games:
            await interaction.followup.send('No active game.', ephemeral=True)
            return
            
        game = self.games[ch_id]
        uid = interaction.user.id
        
        if uid not in game.players:
            await interaction.followup.send('Not in game.', ephemeral=True)
            return
            
        player = game.players[uid]
        
        # Only show player location if they can vent (Impostors and Engineers)
        # Crewmates can view the map but won't see their location highlighted
        current_room = game.get_room(player.location)
        player_vent = None
        if player.can_vent and current_room and current_room.can_vent:
            player_vent = player.location
        
        vent_map_buffer = create_vent_map_image(
            player_vent=player_vent,
            map_layout=game.map_layout
        )
        
        # Create embed with vent information
        embed = discord.Embed(
            title="🕳️ Vent System Map",
            description="All vent locations and connections on The Skeld",
            color=discord.Color.dark_gray()
        )
        
        # Only show location info for players who can vent
        if player.can_vent:
            if player_vent:
                embed.add_field(
                    name="Current Location",
                    value=f"🔴 {player_vent} (You are here)",
                    inline=False
                )
            else:
                embed.add_field(
                    name="Current Location",
                    value=f"📍 {player.location} (No vent access here)",
                    inline=False
                )
        else:
            # Crewmates don't see their location
            embed.add_field(
                name="ℹ️ Information",
                value="As a crewmate, you cannot use vents, but you can study the vent network to track suspicious activity.",
                inline=False
            )
        
        # List all vent locations
        vent_rooms = [room.name for room in game.map_layout.rooms.values() if room.can_vent]
        embed.add_field(
            name="Vent Locations",
            value=", ".join(sorted(vent_rooms)),
            inline=False
        )
        
        # Role-specific tips
        if player.can_vent:
            embed.add_field(
                name="💡 Tip",
                value="Green lines show vent tunnel connections. Use `/vent` in a room with a vent to enter the vent system.",
                inline=False
            )
            
            if player.role == 'Engineer':
                embed.add_field(
                    name="🔧 Engineer Note",
                    value="You can use vents just like impostors, but be careful not to look suspicious!",
                    inline=False
                )
        else:
            embed.add_field(
                name="🔍 Detective Tip",
                value="Watch for players appearing in rooms connected by vents - they might be using the vent system!",
                inline=False
            )
        
        file = discord.File(vent_map_buffer, filename="vent_map.png")
        embed.set_image(url="attachment://vent_map.png")
        
        await interaction.followup.send(file=file, embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(VentCog(bot))
