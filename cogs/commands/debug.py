"""Debug commands for testing (Owner only)"""
import discord
from discord import app_commands, ui
from discord.ext import commands
from typing import Optional

BOT_OWNER_ID = 702136500334100604


class CogReloadSelect(ui.Select):
    """Dropdown select menu for choosing a cog to reload"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
        # Get all loaded cogs
        options = []
        for cog_name in sorted(bot.cogs.keys()):
            options.append(
                discord.SelectOption(
                    label=cog_name,
                    description=f"Reload the {cog_name} cog",
                    value=cog_name
                )
            )
        
        super().__init__(
            placeholder="Select a cog to reload...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Handle cog selection and reload"""
        selected_cog = self.values[0]
        
        # Map cog names to their module paths
        cog_module_map = {
            'LobbyCog': 'cogs.commands.lobby',
            'GameStartCog': 'cogs.commands.game_start',
            'MeetingCog': 'cogs.commands.game_meeting',
            'GameEndCog': 'cogs.commands.game_end',
            'KillCog': 'cogs.commands.game_kill',
            'SabotageCog': 'cogs.commands.game_sabotage',
            'VentCog': 'cogs.commands.game_vent',
            'GhostChatCog': 'cogs.commands.game_ghost',
            'GameStatusCog': 'cogs.commands.game_status',
            'MapCog': 'cogs.commands.game_map',
            'BodyDiscoveryCog': 'cogs.commands.game_bodies',
            'ImpostorsCog': 'cogs.commands.game_impostors',
            'TasksCog': 'cogs.commands.tasks_cmd',
            'DebugCog': 'cogs.commands.debug',
            'ListenerCog': 'cogs.events.listeners',
        }
        
        module_path = cog_module_map.get(selected_cog)
        
        if not module_path:
            await interaction.response.send_message(
                f"❌ Could not find module path for cog: {selected_cog}",
                ephemeral=True
            )
            return
        
        try:
            # Reload the extension
            await self.bot.reload_extension(module_path)
            
            await interaction.response.send_message(
                f"✅ Successfully reloaded **{selected_cog}** (`{module_path}`)",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed to reload **{selected_cog}**:\n```\n{str(e)}\n```",
                ephemeral=True
            )


class CogReloadView(ui.View):
    """View containing the cog reload dropdown"""
    
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=60)
        self.add_item(CogReloadSelect(bot))


class DebugCog(commands.Cog):
    """Debug commands for testing"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.games = getattr(bot, 'amongus_games', {})
        self.forced_impostors = {}  # Format: {channel_id: user_id}
        
    async def cog_load(self):
        print('DebugCog loaded')
    
    @app_commands.command(name='forceimpostor', description='[DEBUG] Force a player to always be impostor (Owner only)')
    @app_commands.describe(
        user='The user to force as impostor',
        enabled='Whether to enable or disable forced impostor (default: True)'
    )
    async def force_impostor(
        self, 
        interaction: discord.Interaction, 
        user: discord.Member,
        enabled: bool = True
    ):
        """Force a specific player to always be assigned as impostor"""
        
        # Check if user is bot owner
        if interaction.user.id != BOT_OWNER_ID:
            await interaction.response.send_message(
                "❌ This command is only available to the bot owner!",
                ephemeral=True
            )
            return
        
        if not interaction.channel:
            await interaction.response.send_message(
                "This command must be used in a server channel.",
                ephemeral=True
            )
            return
        
        ch_id = interaction.channel.id
        
        if enabled:
            self.forced_impostors[ch_id] = user.id
            await interaction.response.send_message(
                f"🔧 **DEBUG MODE ENABLED**\n"
                f"**{user.display_name}** will now **ALWAYS** be assigned as impostor in this channel.\n"
                f"This will take effect when the game starts with `/start`.\n\n"
                f"To disable: `/forceimpostor @{user.display_name} enabled:False`",
                ephemeral=True
            )
        else:
            if ch_id in self.forced_impostors:
                del self.forced_impostors[ch_id]
            await interaction.response.send_message(
                f"🔧 **DEBUG MODE DISABLED**\n"
                f"Forced impostor removed for this channel. Roles will be assigned randomly.",
                ephemeral=True
            )
    
    @app_commands.command(name='debuginfo', description='[DEBUG] Show current debug settings (Owner only)')
    async def debug_info(self, interaction: discord.Interaction):
        """Show current debug settings"""
        
        # Check if user is bot owner
        if interaction.user.id != BOT_OWNER_ID:
            await interaction.response.send_message(
                "❌ This command is only available to the bot owner!",
                ephemeral=True
            )
            return
        
        if not interaction.channel:
            await interaction.response.send_message(
                "This command must be used in a server channel.",
                ephemeral=True
            )
            return
        
        ch_id = interaction.channel.id
        
        embed = discord.Embed(
            title="🔧 Debug Settings",
            color=discord.Color.orange()
        )
        
        if ch_id in self.forced_impostors:
            forced_user_id = self.forced_impostors[ch_id]
            user = interaction.guild.get_member(forced_user_id) if interaction.guild else None
            user_name = user.display_name if user else f"User ID: {forced_user_id}"
            embed.add_field(
                name="Forced Impostor",
                value=f"✅ **{user_name}** will always be impostor",
                inline=False
            )
        else:
            embed.add_field(
                name="Forced Impostor",
                value="❌ No forced impostor set",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name='reloadcog', description='[DEBUG] Reload a specific cog (Owner only)')
    async def reload_cog(self, interaction: discord.Interaction):
        """Reload a specific cog using a dropdown menu"""
        
        # Check if user is bot owner
        if interaction.user.id != BOT_OWNER_ID:
            await interaction.response.send_message(
                "❌ This command is only available to the bot owner!",
                ephemeral=True
            )
            return
        
        # Check if there are any cogs loaded
        if not self.bot.cogs:
            await interaction.response.send_message(
                "❌ No cogs are currently loaded!",
                ephemeral=True
            )
            return
        
        # Send the dropdown view
        view = CogReloadView(self.bot)
        await interaction.response.send_message(
            "🔄 **Reload Cog**\nSelect a cog from the dropdown to reload it:",
            view=view,
            ephemeral=True
        )
    
    def get_forced_impostor(self, channel_id: int) -> Optional[int]:
        """Get the forced impostor user ID for a channel, if any"""
        return self.forced_impostors.get(channel_id)


async def setup(bot: commands.Bot):
    await bot.add_cog(DebugCog(bot))
