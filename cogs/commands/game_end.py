"""End game command"""
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional


class GameEndCog(commands.Cog):
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.games = getattr(bot, 'amongus_games', {})
        self.game_manager = None
    
    async def cog_load(self):
        if hasattr(self.bot, 'game_manager'):
            self.game_manager = getattr(self.bot, 'game_manager')
        print('GameEndCog loaded')
    
    @app_commands.command(name='endgame', description='End the current game (host only)')
    async def endgame(self, interaction: discord.Interaction):
        if interaction.channel is None:
            await interaction.response.send_message(
                'This command must be used in a server channel.', 
                ephemeral=True
            )
            return
        
        ch_id = interaction.channel.id
        
        if ch_id not in self.games:
            await interaction.response.send_message('No active game in this channel.', ephemeral=True)
            return
        
        game = self.games[ch_id]
        
        member = interaction.guild.get_member(interaction.user.id) if interaction.guild else None
        is_admin = member and member.guild_permissions.administrator if member else False
        
        if not is_admin and interaction.user.id not in game.players:
            await interaction.response.send_message(
                'Only admins or players can end the game.', 
                ephemeral=True
            )
            return

        if hasattr(game, 'cancel_all_tasks'):
            game.cancel_all_tasks()
        
        game.active_sabotage = None
        
        game.phase = "ended"
        
        if self.game_manager:
            try:
                await self.game_manager.delete_game(ch_id)
                print(f'✅ Deleted game from database for channel {ch_id}')
            except Exception as e:
                print(f'⚠️  Error deleting game from database: {e}')
        
        if ch_id in self.games:
            del self.games[ch_id]
        
        await interaction.response.send_message(
            '🛑 **Game Ended!**\n'
            'Use `/create` to start a new lobby.',
            ephemeral=False
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(GameEndCog(bot))
