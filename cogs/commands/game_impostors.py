import discord
from discord import app_commands
from discord.ext import commands


class ImpostorsCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.games = getattr(bot, 'amongus_games', {})

    async def cog_load(self):
        print('ImpostorsCog loaded')

    @app_commands.command(name='impostors', description='View your fellow impostors (Impostors only)')
    async def impostors(self, interaction: discord.Interaction):
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
            await interaction.response.send_message("🚫 Only impostors can use this command!", ephemeral=True)
            return

        other_impostors = [
            p for p in game.players.values()
            if p.role == "Impostor" and p.user_id != uid
        ]

        if not other_impostors:
            await interaction.response.send_message(
                "🔪 **You are the only impostor!**\n\nGood luck eliminating the crew on your own!",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🔪 Your Fellow Impostors",
            description="Work together to eliminate the crew!",
            color=discord.Color.red()
        )

        impostor_list = []
        for imp in other_impostors:
            status = "💀 Dead" if not imp.alive else "✅ Alive"
            location = imp.location if imp.alive else "N/A"
            impostor_list.append(f"**{imp.name}** - {status} ({location})")

        embed.add_field(
            name=f"Team Members ({len(other_impostors)})",
            value="\n".join(impostor_list),
            inline=False
        )

        alive_impostors = len([i for i in other_impostors if i.alive])
        total_impostors = len(other_impostors) + 1
        alive_crew = len(game.alive_crewmates())

        embed.add_field(
            name="Game Status",
            value=f"🔪 Alive Impostors: {alive_impostors + 1}/{total_impostors}\n👷 Alive Crew: {alive_crew}",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ImpostorsCog(bot))
