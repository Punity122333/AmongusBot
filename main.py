import os
import discord
import asyncio
from discord.ext import commands
from dotenv import load_dotenv
from typing import Optional
from amongus.database import GameDatabase
from amongus.game_manager import GameManager

load_dotenv()
TOKEN = os.getenv('DC3')
APPLICATION_ID = os.getenv('AP3')
DEV_GUILD_ID = os.getenv('DEV_GUILD_ID')
DEV_GUILD_IDS = [gid.strip() for gid in DEV_GUILD_ID.split(',')] if DEV_GUILD_ID else []

intents = discord.Intents.default()
intents.guilds = True
intents.members = True 

COG_PATHS = [
    'cogs.commands.lobby',
    'cogs.commands.game_start',
    'cogs.commands.game_meeting',
    'cogs.commands.game_end',
    'cogs.commands.game_kill',
    'cogs.commands.game_sabotage',
    'cogs.commands.game_vent',
    'cogs.commands.game_ghost',
    'cogs.commands.game_status',
    'cogs.commands.game_map',
    'cogs.commands.game_bodies',
    'cogs.commands.game_impostors',
    'cogs.commands.game_shield',
    'cogs.commands.tasks_cmd',
    'cogs.commands.debug',
    'cogs.events.listeners',
]

class MyBot(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db: Optional[GameDatabase] = None
        self.game_manager: Optional[GameManager] = None
        self.amongus_games = {}

    async def setup_hook(self) -> None:
        print('🔄 Starting setup...')
        
        print('🗄️  Initializing database...')
        self.db = GameDatabase("amongus.db")
        await self.db.initialize()
        
        self.game_manager = GameManager(self.db)
        self.amongus_games = self.game_manager._cache
        
        print('✅ Database and game manager ready!')
        
        print('🧹 Clearing all existing commands...')
        try:
            self.tree.clear_commands(guild=None)
            await self.tree.sync()
            print('✅ Cleared global commands')
            
            if DEV_GUILD_IDS:
                for guild_id in DEV_GUILD_IDS:
                    guild = discord.Object(id=int(guild_id))
                    self.tree.clear_commands(guild=guild)
                    await self.tree.sync(guild=guild)
                    print(f'✅ Cleared guild commands for {guild_id}')
        except Exception as e:
            print(f'⚠️  Error clearing commands: {e}')

        print('\n📦 Loading cogs...')
        for cog in COG_PATHS:
            try:
                await self.load_extension(cog)
                print(f'✅ Loaded {cog}')
            except Exception as e:
                print(f'❌ Failed to load {cog}: {e}')

        print(f'\n📋 Commands in tree: {len(self.tree.get_commands())}')
        for cmd in self.tree.get_commands():
            print(f'  - {cmd.name}')

        if DEV_GUILD_IDS:
            print(f'\n🏢 DEV MODE: Syncing commands to {len(DEV_GUILD_IDS)} guild(s)...')
            for guild_id in DEV_GUILD_IDS:
                try:
                    guild = discord.Object(id=int(guild_id))
                    self.tree.clear_commands(guild=guild)
                    self.tree.copy_global_to(guild=guild)
                    synced_guild = await self.tree.sync(guild=guild)
                    print(f'✅ Synced {len(synced_guild)} commands to guild {guild_id} (instant)')
                    
                    if len(synced_guild) == 0:
                        print(f'⚠️  WARNING: Synced 0 commands to guild {guild_id}!')
                        print('   This usually means the bot lacks "applications.commands" scope.')
                        print(f'   Re-invite your bot using this URL:')
                        print(f'   https://discord.com/api/oauth2/authorize?client_id={self.application_id}&permissions=8&scope=bot%20applications.commands')
                    else:
                        print(f'✅ Guild sync successful for {guild_id}!')
                        for cmd in synced_guild:
                            print(f'  - /{cmd.name}')
                except Exception as e:
                    print(f'❌ Failed to sync to guild {guild_id}: {e}')
                    import traceback
                    traceback.print_exc()
        else:
            print('\n🌍 PRODUCTION MODE: Syncing commands globally...')
            try:
                synced = await self.tree.sync()
                print(f'✅ Synced {len(synced)} commands globally (may take up to 1 hour to appear)')
                for cmd in synced:
                    print(f'  - /{cmd.name}')
            except Exception as e:
                print(f'❌ Failed to sync globally: {e}')
                import traceback
                traceback.print_exc()
                return
        
        print('\n🎉 Setup complete!')
        if DEV_GUILD_IDS:
            print(f'📝 Note: Commands synced to {len(DEV_GUILD_IDS)} dev guild(s) ONLY (not global)')

application_id = None
if APPLICATION_ID:
    try:
        application_id = int(APPLICATION_ID)
    except Exception:
        print('Invalid APPLICATION_ID in env; ignoring')

bot = MyBot(command_prefix='/', intents=intents, application_id=application_id)

@bot.event
async def on_ready():
    if bot.user:
        print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    else:
        print('Logged in, but bot.user is None')
    print('------')

async def shutdown():
    print('\n🛑 Shutting down...')
    if bot.db:
        await bot.db.close()
    print('✅ Cleanup complete')

if __name__ == '__main__':
    if TOKEN is None:
        raise ValueError('DISCORD_TOKEN environment variable not set')
    try:
        bot.run(TOKEN)
    except KeyboardInterrupt:
        import asyncio
        asyncio.run(shutdown())
    except discord.errors.PrivilegedIntentsRequired:
        print('\nPrivileged intents required but not enabled for this application.')
        print('Go to https://discord.com/developers/applications, open your application,')
        print('navigate to "Bot" and enable the "Server Members Intent" and/or "Presence Intent" as needed.')
        raise
