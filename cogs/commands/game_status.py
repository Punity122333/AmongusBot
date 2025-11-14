"""Game status and progress tracking"""
import discord
from discord import app_commands
from discord.ext import commands


class GameStatusCog(commands.Cog):
    """Commands for viewing game status"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.games = getattr(bot, 'amongus_games', {})
        
    async def cog_load(self):
        print('GameStatusCog loaded')
        
    @app_commands.command(name='gamestatus', description='View overall game progress and stats')
    async def gamestatus(self, interaction: discord.Interaction):
        if not interaction.channel:
            await interaction.response.send_message('Use in a server channel.', ephemeral=True)
            return
            
        ch_id = interaction.channel.id
        if ch_id not in self.games:
            await interaction.response.send_message('No active game.', ephemeral=True)
            return
            
        game = self.games[ch_id]
        
        # Calculate overall task progress for all crewmate roles
        crewmates = [p for p in game.players.values() if p.role in ['Crewmate', 'Scientist', 'Engineer']]
        if crewmates:
            total_tasks = sum(p.total_tasks for p in crewmates)
            completed_tasks = sum(p.completed_tasks for p in crewmates)
            task_percent = int((completed_tasks / total_tasks * 100)) if total_tasks > 0 else 0
            filled = int(task_percent / 10)
            task_bar = "█" * filled + "░" * (10 - filled)
        else:
            completed_tasks = 0
            total_tasks = 0
            task_percent = 0
            task_bar = "░" * 10
            
        # Count alive/dead by role
        alive_players = game.alive_players()
        alive_crewmates = [p for p in alive_players if p.role == 'Crewmate']
        alive_scientists = [p for p in alive_players if p.role == 'Scientist']
        alive_engineers = [p for p in alive_players if p.role == 'Engineer']
        alive_impostors = game.alive_impostors()
        
        total_crew_alive = len(alive_crewmates) + len(alive_scientists) + len(alive_engineers)
        
        embed = discord.Embed(
            title="🎮 Game Status",
            description=f"**Phase:** {game.phase.title()}\n**Game Code:** `{game.game_code}`",
            color=discord.Color.blue()
        )
        
        # Overall task progress
        embed.add_field(
            name="📊 Task Progress (All Crewmates)",
            value=f"`{task_bar}` {completed_tasks}/{total_tasks} ({task_percent}%)",
            inline=False
        )
        
        # Player counts
        embed.add_field(
            name="👥 Players",
            value=f"**Alive:** {len(alive_players)}\n**Dead:** {len(game.players) - len(alive_players)}",
            inline=True
        )
        
        embed.add_field(
            name="🔧 Crew Team (Alive)",
            value=f"👷 Crewmates: {len(alive_crewmates)}\n" +
                  (f"🧪 Scientists: {len(alive_scientists)}\n" if len(alive_scientists) > 0 else "") +
                  (f"🔩 Engineers: {len(alive_engineers)}\n" if len(alive_engineers) > 0 else "") +
                  f"**Total: {total_crew_alive}**",
            inline=True
        )
        
        embed.add_field(
            name="🔪 Impostors",
            value=f"**Alive:** {len(alive_impostors)}",
            inline=True
        )
        
        # Sabotage status with timer information
        if hasattr(game, 'active_sabotage') and game.active_sabotage:
            sabotage_info = {
                'o2': '🔴 **OXYGEN DEPLETION** - Critical! Fix immediately!',
                'reactor': '☢️ **REACTOR MELTDOWN** - Critical! Stabilize now!',
                'electrical': '⚡ **ELECTRICAL FAILURE** - Systems failing!',
                'communications': '📡 **COMMUNICATIONS OFFLINE** - Task info hidden!',
                'doors': '🚪 **DOORS LOCKED** - Movement restricted!'
            }
            sabotage_msg = sabotage_info.get(game.active_sabotage, game.active_sabotage.upper())
            embed.add_field(
                name="🚨 Active Sabotage",
                value=sabotage_msg,
                inline=False
            )
            
        # Win condition progress
        if len(alive_impostors) >= total_crew_alive and len(alive_impostors) > 0:
            embed.add_field(
                name="⚠️ WARNING",
                value="Impostors are about to win! Impostors equal or outnumber crewmates!",
                inline=False
            )
        elif task_percent >= 80:
            embed.add_field(
                name="🎯 Near Victory",
                value="Crewmates are close to winning through tasks!",
                inline=False
            )
            
        embed.set_footer(text="Use /tasks to see your personal task list")
        
        await interaction.response.send_message(embed=embed, ephemeral=False)
    
    @app_commands.command(name='viewalive', description='View all alive players in the game')
    async def viewalive(self, interaction: discord.Interaction):
        if not interaction.channel:
            await interaction.response.send_message('Use in a server channel.', ephemeral=True)
            return
            
        ch_id = interaction.channel.id
        if ch_id not in self.games:
            await interaction.response.send_message('No active game.', ephemeral=True)
            return
            
        game = self.games[ch_id]
        
        if game.phase == 'lobby':
            await interaction.response.send_message('Game has not started yet. Use `/viewlobby` to see lobby players.', ephemeral=True)
            return
        
        await interaction.response.defer(thinking=True)
        
        # Get alive players
        alive_players = game.alive_players()
        
        if not alive_players:
            await interaction.followup.send('No players are alive!', ephemeral=True)
            return
        
        # Generate alive players card
        from amongus.card_generator import create_alive_players_card
        players_data = [p.to_dict() for p in alive_players]
        card_buffer = await create_alive_players_card(players_data, game.game_code)
        
        file = discord.File(card_buffer, filename="alive_players.png")
        
        # Create embed
        embed = discord.Embed(
            title="👥 Alive Players",
            description=f"**Game Code:** `{game.game_code}`\n**Phase:** {game.phase.title()}",
            color=discord.Color.green()
        )
        
        # Count by role (but don't reveal roles)
        embed.add_field(
            name="Status",
            value=f"**Alive:** {len(alive_players)}\n**Dead:** {len(game.players) - len(alive_players)}",
            inline=True
        )
        
        embed.set_image(url="attachment://alive_players.png")
        
        await interaction.followup.send(embed=embed, file=file)


async def setup(bot: commands.Bot):
    await bot.add_cog(GameStatusCog(bot))
