"""Ghost chat for dead players"""
import discord
import asyncio
from discord import app_commands
from discord.ext import commands
from typing import cast


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


class GhostChatCog(commands.Cog):
    """Ghost chat for dead players"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.games = getattr(bot, 'amongus_games', {})
        
    async def cog_load(self):
        print('GhostChatCog loaded')
        
    @app_commands.command(name='ghostchat', description='Send a message to other dead players')
    @app_commands.describe(message='Your message to other ghosts')
    async def ghostchat(self, interaction: discord.Interaction, message: str):
        if not interaction.channel or not interaction.guild:
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
        
        if player.alive:
            await interaction.response.send_message('👻 Only dead players can use ghost chat!', ephemeral=True)
            return
            
        dead_players = [p for p in game.players.values() if not p.alive and not p.is_bot]
        
        if len(dead_players) <= 1:
            await interaction.response.send_message(
                '👻 You are the only ghost! Message sent to the void...',
                ephemeral=True
            )
            return
            
        sent_count = 0
        for p in dead_players:
            if p.user_id == uid:
                continue
                
            user = interaction.guild.get_member(p.user_id) if interaction.guild else None
            if user:
                try:
                    embed = discord.Embed(
                        title="👻 Ghost Chat",
                        description=f"**{player.name}:** {message}",
                        color=discord.Color.purple()
                    )
                    await safe_dm_user(user, embed=embed)
                    sent_count += 1
                except Exception:
                    pass
                    
        await interaction.response.send_message(
            f'👻 Ghost message sent to {sent_count} dead player(s)!',
            ephemeral=True
        )
        
    @app_commands.command(name='ghoststatus', description='View all dead players')
    async def ghoststatus(self, interaction: discord.Interaction):
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
        
        if player.alive:
            await interaction.response.send_message('👻 You must be dead to see ghost status!', ephemeral=True)
            return
            
        dead_players = [p for p in game.players.values() if not p.alive]
        
        if not dead_players:
            await interaction.response.send_message('👻 No dead players yet!', ephemeral=True)
            return
            
        embed = discord.Embed(
            title="👻 Dead Players (Ghost Chat)",
            description="These players can see each other's ghost messages:",
            color=discord.Color.purple()
        )
        
        ghost_list = []
        for p in dead_players:
            bot_tag = " [BOT]" if p.is_bot else ""
            role_emoji = "🔪" if p.role == "Impostor" else "🔧"
            ghost_list.append(f"{role_emoji} {p.name}{bot_tag}")
            
        embed.add_field(
            name=f"Ghosts ({len(dead_players)})",
            value="\n".join(ghost_list),
            inline=False
        )
        
        embed.set_footer(text="Use /ghostchat <message> to chat with other ghosts!")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(GhostChatCog(bot))
