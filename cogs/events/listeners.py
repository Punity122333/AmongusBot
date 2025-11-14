import discord
from discord.ext import commands


class ListenerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        print("ListenerCog loaded")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):

        pass


async def setup(bot: commands.Bot):
    await bot.add_cog(ListenerCog(bot))
