import discord
from discord import app_commands
from discord.ext import commands
from amongus.map_renderer import create_map_image
from .game_bodies import notify_body_discovery


class MapCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.games = getattr(bot, "amongus_games", {})

    async def cog_load(self):
        pass

    @app_commands.command(name='move', description='Move to a connected room')
    @app_commands.describe(room='The room to move to')
    async def move(self, interaction: discord.Interaction, room: str):
        await interaction.response.defer(ephemeral=True)
        
        ch_id = interaction.channel_id
        uid = interaction.user.id
        
        if ch_id not in self.games:
            await interaction.followup.send("❌ No active game in this channel!", ephemeral=True)
            return
        
        game = self.games[ch_id]
        
        if game.phase != 'tasks':
            await interaction.followup.send("❌ You can only move during the task phase!", ephemeral=True)
            return
        
        if uid not in game.players:
            await interaction.followup.send("❌ You are not in this game!", ephemeral=True)
            return
        
        player = game.players[uid]
        
        if not player.alive:
            await interaction.followup.send("❌ Ghosts cannot move between rooms!", ephemeral=True)
            return
        
        # Check if doors are sabotaged
        if hasattr(game, 'active_sabotage') and game.active_sabotage == 'doors':
            await interaction.followup.send(
                "🚪 **DOORS LOCKED!**\n\n"
                "Movement is restricted due to the doors sabotage.\n"
                "Wait for the doors to unlock automatically or for someone to fix the sabotage!",
                ephemeral=True
            )
            return
        
        current_location = player.location
        
        room_map = {r.lower(): r for r in game.map_layout.rooms.keys()}
        room_lower = room.lower()
        
        if room_lower not in room_map:
            await interaction.followup.send(f"❌ Room '{room}' does not exist!", ephemeral=True)
            return
        
        actual_room_name = room_map[room_lower]
        target_room_obj = game.get_room(actual_room_name)
        
        if not target_room_obj:
            await interaction.followup.send(f"❌ Room '{room}' does not exist!", ephemeral=True)
            return
        
        if not game.map_layout.is_connected(current_location, actual_room_name):
            await interaction.followup.send(
                f"❌ You cannot move from **{current_location}** to **{actual_room_name}**!\n"
                f"You can only move to: {', '.join(game.get_room(current_location).connected_rooms)}",
                ephemeral=True
            )
            return
        
        success = game.move_player(uid, actual_room_name)
        
        if success:
            await interaction.followup.send(f"✅ Moved from **{current_location}** → **{actual_room_name}**", ephemeral=True)
            
            if target_room_obj.bodies and not player.is_bot:
                channel = interaction.channel
                if isinstance(channel, discord.TextChannel):
                    for body_name in target_room_obj.bodies:
                        victim = next((p for p in game.players.values() if p.name == body_name), None)
                        if victim:
                            await notify_body_discovery(
                                self.bot,
                                game,
                                channel,
                                victim,
                                actual_room_name,
                                player.user_id
                            )
        else:
            await interaction.followup.send(f"❌ Failed to move to {actual_room_name}!", ephemeral=True)

    @app_commands.command(name='map', description='View the map with your current location')
    async def map_view(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        ch_id = interaction.channel_id
        uid = interaction.user.id
        
        if ch_id not in self.games:
            await interaction.followup.send("❌ No active game in this channel!", ephemeral=True)
            return
        
        game = self.games[ch_id]
        
        if uid not in game.players:
            await interaction.followup.send("❌ You are not in this game!", ephemeral=True)
            return
        
        player = game.players[uid]
        current_room = player.location
        room_obj = game.get_room(current_room)
        
        sabotaged_rooms = []
        if game.active_sabotage:
            sabotaged_rooms = [game.active_sabotage]
        
        map_buffer = create_map_image(
            player_room=current_room,
            sabotaged_rooms=sabotaged_rooms,
            map_layout=game.map_layout
        )
        
        embed = discord.Embed(
            title="🗺️ The Skeld Map",
            description=f"**Your Location:** {current_room}",
            color=discord.Color.blue()
        )
        
        if room_obj:
            connected = ", ".join(room_obj.connected_rooms)
            embed.add_field(
                name="Connected Rooms",
                value=connected,
                inline=False
            )
            
            players_in_room = [p.name for p in game.players.values() if p.location == current_room and p.alive and p.user_id != uid]
            if players_in_room:
                embed.add_field(
                    name="👥 Players in this room",
                    value=", ".join(players_in_room),
                    inline=False
                )
            
            if room_obj.bodies:
                embed.add_field(
                    name="⚠️ Bodies in this room",
                    value=", ".join(room_obj.bodies),
                    inline=False
                )
        
        file = discord.File(fp=map_buffer, filename="map.png")
        embed.set_image(url="attachment://map.png")
        
        await interaction.followup.send(embed=embed, file=file, ephemeral=True)

    @app_commands.command(name='whereami', description='Show your current location and available commands')
    async def whereami(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        ch_id = interaction.channel_id
        uid = interaction.user.id
        
        if ch_id not in self.games:
            await interaction.followup.send("❌ No active game in this channel!", ephemeral=True)
            return
        
        game = self.games[ch_id]
        
        if uid not in game.players:
            await interaction.followup.send("❌ You are not in this game!", ephemeral=True)
            return
        
        player = game.players[uid]
        current_room = player.location
        room_obj = game.get_room(current_room)
        
        embed = discord.Embed(
            title=f"📍 Location: {current_room}",
            color=discord.Color.green()
        )
        
        if room_obj:
            connected = ", ".join(room_obj.connected_rooms)
            embed.add_field(
                name="Connected Rooms",
                value=connected,
                inline=False
            )
            
            if room_obj.has_tasks:
                tasks_here = [(idx, t) for idx, t in enumerate(player.tasks) if t.location == current_room]
                if tasks_here:
                    task_list = "\n".join([f"{idx+1}. {t}" for idx, t in tasks_here])
                    embed.add_field(
                        name="Your Tasks Here",
                        value=task_list,
                        inline=False
                    )
            
            if player.role == 'Impostor' and room_obj.can_vent:
                embed.add_field(
                    name="🕳️ Vent Available",
                    value="Use `/vent` to enter the vent system",
                    inline=False
                )
            
            if room_obj.bodies:
                embed.add_field(
                    name="Bodies Present",
                    value=", ".join(room_obj.bodies),
                    inline=False
                )
        
        status_text = "👻 Ghost" if not player.alive else "✅ Alive"
        embed.add_field(
            name="Status",
            value=status_text,
            inline=True
        )
        
        embed.add_field(
            name="Role",
            value=player.role if player.alive or game.phase == 'ended' else "???",
            inline=True
        )
        
        # Show fast travel info for alive players
        if player.alive:
            embed.add_field(
                name="Fast Travels",
                value=f"🎫 {player.fast_travels_remaining}/3 remaining",
                inline=True
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name='fasttravel', description='Instantly travel to any room (limited uses)')
    @app_commands.describe(room='The room to fast travel to')
    async def fasttravel(self, interaction: discord.Interaction, room: str):
        if not interaction.channel:
            await interaction.response.send_message("Use in a server channel.", ephemeral=True)
            return
            
        await interaction.response.defer(ephemeral=True)
        
        ch_id = interaction.channel.id
        uid = interaction.user.id
        
        if ch_id not in self.games:
            await interaction.followup.send("❌ No active game in this channel!", ephemeral=True)
            return
        
        game = self.games[ch_id]
        
        if game.phase != 'tasks':
            await interaction.followup.send("❌ You can only fast travel during the task phase!", ephemeral=True)
            return
        
        if uid not in game.players:
            await interaction.followup.send("❌ You are not in this game!", ephemeral=True)
            return
        
        player = game.players[uid]
        
        if not player.alive:
            await interaction.followup.send("❌ Ghosts cannot fast travel!", ephemeral=True)
            return
        
        if hasattr(game, 'active_sabotage') and game.active_sabotage == 'doors':
            await interaction.followup.send(
                "🚪 **DOORS LOCKED!**\n\n"
                "Fast travel is disabled due to the doors sabotage.\n"
                "Wait for the doors to unlock automatically!",
                ephemeral=True
            )
            return
        
        if player.fast_travels_remaining <= 0:
            await interaction.followup.send(
                "❌ You have no fast travels remaining!\n"
                f"💡 Use `/move <room>` to travel normally between connected rooms.",
                ephemeral=True
            )
            return
        
        current_location = player.location
        
        room_map = {r.lower(): r for r in game.map_layout.rooms.keys()}
        room_lower = room.lower()
        
        if room_lower not in room_map:
            available_rooms = ", ".join(sorted(game.map_layout.rooms.keys()))
            await interaction.followup.send(
                f"❌ Room '{room}' does not exist!\n"
                f"**Available rooms:** {available_rooms}",
                ephemeral=True
            )
            return
        
        actual_room_name = room_map[room_lower]
        target_room_obj = game.get_room(actual_room_name)
        
        if not target_room_obj:
            await interaction.followup.send(f"❌ Room '{room}' does not exist!", ephemeral=True)
            return
        
        if current_location == actual_room_name:
            await interaction.followup.send(f"❌ You are already in **{actual_room_name}**!", ephemeral=True)
            return
        
        player.location = actual_room_name
        player.fast_travels_remaining -= 1
        
        embed = discord.Embed(
            title="⚡ Fast Travel Successful!",
            description=f"Traveled from **{current_location}** → **{actual_room_name}**",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="Fast Travels Remaining",
            value=f"🎫 {player.fast_travels_remaining}/3",
            inline=True
        )
        
        if target_room_obj.has_tasks:
            tasks_here = [t for t in player.tasks if t.location == actual_room_name and not t.completed]
            if tasks_here:
                task_list = "\n".join([f"• {t.name}" for t in tasks_here])
                embed.add_field(
                    name="📋 Tasks Available Here",
                    value=task_list,
                    inline=False
                )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        if target_room_obj.bodies and not player.is_bot:
            channel = interaction.channel
            if isinstance(channel, discord.TextChannel):
                for body_name in target_room_obj.bodies:
                    victim = next((p for p in game.players.values() if p.name == body_name), None)
                    if victim:
                        await notify_body_discovery(
                            self.bot,
                            game,
                            channel,
                            victim,
                            actual_room_name,
                            player.user_id
                        )


async def setup(bot: commands.Bot):
    await bot.add_cog(MapCog(bot))
