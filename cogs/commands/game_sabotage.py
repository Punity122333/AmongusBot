"""Sabotage system for impostors"""

import discord
from discord import app_commands, ui
from discord.ext import commands
import asyncio
import random
from typing import cast, Optional, Literal
from .game_utils import check_and_announce_winner


class SabotageView(ui.View):
    """Interactive sabotage UI for impostors"""

    def __init__(self, game, channel, bot=None):
        super().__init__(timeout=30)
        self.game = game
        self.channel = channel
        self.bot = bot
        self.sabotaged = False

    @ui.button(label="⚡ Electrical", style=discord.ButtonStyle.danger, emoji="💡")
    async def electrical(self, interaction: discord.Interaction, button: ui.Button):
        if self.sabotaged:
            await interaction.response.send_message(
                "Already sabotaged!", ephemeral=True
            )
            return

        self.sabotaged = True
        self.stop()

        uid = interaction.user.id
        if uid in self.game.players:
            self.game.players[uid].sabotage_cooldown = self.game.kill_cooldown

        await interaction.response.send_message(
            "⚡ Electrical sabotaged!", ephemeral=True
        )
        await self.channel.send(
            "🚨 **SABOTAGE!** ⚡ **ELECTRICAL FAILURE**\n"
            "Crewmates must fix the lights! Use `/fixsabotage electrical`"
        )

        self.game.active_sabotage = "electrical"
        task = asyncio.create_task(self._sabotage_timer())
        if hasattr(self.game, 'background_tasks'):
            self.game.background_tasks.add(task)
            task.add_done_callback(lambda t: self.game.background_tasks.discard(t) if hasattr(self.game, 'background_tasks') else None)

    @ui.button(label="🔴 O2", style=discord.ButtonStyle.danger, emoji="💨")
    async def oxygen(self, interaction: discord.Interaction, button: ui.Button):
        if self.sabotaged:
            await interaction.response.send_message(
                "Already sabotaged!", ephemeral=True
            )
            return

        self.sabotaged = True
        self.stop()

        uid = interaction.user.id
        if uid in self.game.players:
            self.game.players[uid].sabotage_cooldown = self.game.kill_cooldown

        await interaction.response.send_message("💨 O2 sabotaged!", ephemeral=True)
        await self.channel.send(
            "🚨 **SABOTAGE!** 🔴 **OXYGEN DEPLETION**\n"
            "Crewmates have 60 seconds to fix O2! Use `/fixsabotage o2`"
        )

        self.game.active_sabotage = "o2"
        task = asyncio.create_task(self._sabotage_timer())
        if hasattr(self.game, 'background_tasks'):
            self.game.background_tasks.add(task)
            task.add_done_callback(lambda t: self.game.background_tasks.discard(t) if hasattr(self.game, 'background_tasks') else None)

    @ui.button(label="🚪 Doors", style=discord.ButtonStyle.secondary, emoji="🔒")
    async def doors(self, interaction: discord.Interaction, button: ui.Button):
        if self.sabotaged:
            await interaction.response.send_message(
                "Already sabotaged!", ephemeral=True
            )
            return

        self.sabotaged = True
        self.stop()

        uid = interaction.user.id
        if uid in self.game.players:
            self.game.players[uid].sabotage_cooldown = self.game.kill_cooldown

        await interaction.response.send_message("🔒 Doors locked!", ephemeral=True)
        await self.channel.send(
            "🚨 **SABOTAGE!** 🚪 **DOORS LOCKED**\n"
            "Movement and fast travel are restricted for 10 seconds!"
        )

        self.game.active_sabotage = "doors"
        task = asyncio.create_task(self._sabotage_timer())
        if hasattr(self.game, 'background_tasks'):
            self.game.background_tasks.add(task)
            task.add_done_callback(lambda t: self.game.background_tasks.discard(t) if hasattr(self.game, 'background_tasks') else None)

    @ui.button(label="📡 Communications", style=discord.ButtonStyle.danger, emoji="📶")
    async def communications(self, interaction: discord.Interaction, button: ui.Button):
        if self.sabotaged:
            await interaction.response.send_message(
                "Already sabotaged!", ephemeral=True
            )
            return

        self.sabotaged = True
        self.stop()

        uid = interaction.user.id
        if uid in self.game.players:
            self.game.players[uid].sabotage_cooldown = self.game.kill_cooldown

        await interaction.response.send_message("📡 Communications sabotaged!", ephemeral=True)
        await self.channel.send(
            "🚨 **SABOTAGE!** 📡 **COMMUNICATIONS OFFLINE**\n"
            "⚠️ Task lists and locations are hidden!\n"
            "Crewmates must fix communications! Use `/fixsabotage communications`"
        )

        self.game.active_sabotage = "communications"
        task = asyncio.create_task(self._sabotage_timer())
        if hasattr(self.game, 'background_tasks'):
            self.game.background_tasks.add(task)
            task.add_done_callback(lambda t: self.game.background_tasks.discard(t) if hasattr(self.game, 'background_tasks') else None)

    @ui.button(label="☢️ Reactor", style=discord.ButtonStyle.danger, emoji="⚛️")
    async def reactor(self, interaction: discord.Interaction, button: ui.Button):
        if self.sabotaged:
            await interaction.response.send_message(
                "Already sabotaged!", ephemeral=True
            )
            return

        self.sabotaged = True
        self.stop()

        uid = interaction.user.id
        if uid in self.game.players:
            self.game.players[uid].sabotage_cooldown = self.game.kill_cooldown

        await interaction.response.send_message("☢️ Reactor sabotaged!", ephemeral=True)
        await self.channel.send(
            "🚨 **SABOTAGE!** ☢️ **REACTOR MELTDOWN**\n"
            "Crewmates have 45 seconds to stabilize the reactor! Use `/fixsabotage reactor`"
        )

        self.game.active_sabotage = "reactor"
        task = asyncio.create_task(self._sabotage_timer())
        if hasattr(self.game, 'background_tasks'):
            self.game.background_tasks.add(task)
            task.add_done_callback(lambda t: self.game.background_tasks.discard(t) if hasattr(self.game, 'background_tasks') else None)

    async def _sabotage_timer(self):
        """Handle sabotage timer and auto-fix"""
        try:
            if self.game.active_sabotage == "o2":
                await asyncio.sleep(60)
                if self.game.active_sabotage == "o2" and self.game.phase != "ended":

                    self.game.active_sabotage = None
                    await check_and_announce_winner(
                        self.game,
                        self.channel,
                        "sabotageO2 ran out! Crewmates failed to fix the sabotage in time!",
                        self.bot
                    )
            elif self.game.active_sabotage == "reactor":
                await asyncio.sleep(45)
                if self.game.active_sabotage == "reactor" and self.game.phase != "ended":

                    self.game.active_sabotage = None
                    await check_and_announce_winner(
                        self.game,
                        self.channel,
                        "sabotageReactor meltdown! Crewmates failed to stabilize in time!",
                        self.bot
                    )
            elif self.game.active_sabotage == "electrical":
                await asyncio.sleep(90)
                if self.game.active_sabotage == "electrical" and self.game.phase != "ended":

                    self.game.active_sabotage = None
                    await check_and_announce_winner(
                        self.game,
                        self.channel,
                        "sabotageElectrical failure caused critical systems to fail!",
                        self.bot
                    )
            elif self.game.active_sabotage == "doors":
                await asyncio.sleep(10)
                if self.game.active_sabotage == "doors" and self.game.phase != "ended":
                    await self.channel.send("🔓 Doors automatically unlocked!")
                    self.game.active_sabotage = None
            elif self.game.active_sabotage == "communications":
                await asyncio.sleep(45)
                if self.game.active_sabotage == "communications" and self.game.phase != "ended":
                    await self.channel.send("📡 Communications automatically restored!")
                    self.game.active_sabotage = None
        except asyncio.CancelledError:

            pass


class FixSabotageView(ui.View):
    """Interactive sabotage fix UI"""

    def __init__(self, sabotage_type: str, game, channel, player):
        super().__init__(timeout=30)
        self.sabotage_type = sabotage_type
        self.game = game
        self.channel = channel
        self.player = player
        self.progress = 0
        self.started = False
        self.failed = False

        base_time = 20.0
        self.fix_time = base_time / player.sabotage_fix_speed
        self.time_remaining = self.fix_time
        self.timer_task = None

    async def start_timer(self, interaction: discord.Interaction):
        """Start the countdown timer"""
        self.started = True
        self.timer_task = asyncio.create_task(self._countdown())
    
    async def _countdown(self):
        """Countdown timer that updates the message"""
        try:
            while self.time_remaining > 0 and not self.failed:
                await asyncio.sleep(1)
                self.time_remaining -= 1
                
            if self.time_remaining <= 0 and not self.failed:

                self.failed = True
                self.stop()
        except asyncio.CancelledError:
            pass

    def _get_progress_bar(self) -> str:
        """Generate a progress bar for the timer"""
        if self.fix_time == 0:
            return "░░░░░░░░░░"
        percent = self.time_remaining / self.fix_time
        filled = int(percent * 10)
        return "█" * filled + "░" * (10 - filled)
    
    def _format_time(self) -> str:
        """Format time remaining"""
        return f"{int(self.time_remaining)}s"

    @ui.button(label="Fix Part 1", style=discord.ButtonStyle.primary, emoji="🔧")
    async def fix_part1(self, interaction: discord.Interaction, button: ui.Button):
        if not self.started:
            await self.start_timer(interaction)
        
        if self.failed:
            await interaction.response.send_message("⏰ Time's up! Failed to fix the sabotage.", ephemeral=True)
            return
        
        self.progress += 1
        button.disabled = True

        if self.progress >= 2:

            if self.timer_task:
                self.timer_task.cancel()
            
            await interaction.response.edit_message(
                content="✅ Sabotage fixed!", view=None
            )
            self.stop()
            self.game.active_sabotage = None

            bonus_msg = ""
            if self.player.role == 'Engineer':
                bonus_msg = " ⚙️ *Engineer speed bonus applied!*"
            
            await self.channel.send(
                f"✅ **{interaction.user.display_name}** fixed the {self.sabotage_type} sabotage!{bonus_msg}"
            )
        else:
            progress_bar = self._get_progress_bar()
            time_str = self._format_time()
            await interaction.response.edit_message(
                content=f"🔧 Fixing... ({self.progress}/2)\n⏱️ Time: `{progress_bar}` {time_str}",
                view=self
            )

    @ui.button(label="Fix Part 2", style=discord.ButtonStyle.primary, emoji="🔨")
    async def fix_part2(self, interaction: discord.Interaction, button: ui.Button):
        if not self.started:
            await self.start_timer(interaction)
        
        if self.failed:
            await interaction.response.send_message("⏰ Time's up! Failed to fix the sabotage.", ephemeral=True)
            return
        
        self.progress += 1
        button.disabled = True

        if self.progress >= 2:

            if self.timer_task:
                self.timer_task.cancel()
            
            await interaction.response.edit_message(
                content="✅ Sabotage fixed!", view=None
            )
            self.stop()
            self.game.active_sabotage = None
            

            bonus_msg = ""
            if self.player.role == 'Engineer':
                bonus_msg = " ⚙️ *Engineer speed bonus applied!*"
            
            await self.channel.send(
                f"✅ **{interaction.user.display_name}** fixed the {self.sabotage_type} sabotage!{bonus_msg}"
            )
        else:
            progress_bar = self._get_progress_bar()
            time_str = self._format_time()
            await interaction.response.edit_message(
                content=f"🔧 Fixing... ({self.progress}/2)\n⏱️ Time: `{progress_bar}` {time_str}",
                view=self
            )


class SabotageCog(commands.Cog):
    """Commands for sabotage mechanics"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.games = getattr(bot, "amongus_games", {})
        
        asyncio.create_task(self._sabotage_cooldown_loop())

    async def cog_load(self):
        print("SabotageCog loaded")

    async def _sabotage_cooldown_loop(self):
        while True:
            await asyncio.sleep(1)
            for game in self.games.values():
                if game.phase == "tasks":
                    for player in game.players.values():
                        if player.role == "Impostor" and player.sabotage_cooldown > 0:
                            player.sabotage_cooldown -= 1

    @app_commands.command(
        name="sabotage", description="Sabotage systems (Impostors only)"
    )
    async def sabotage(self, interaction: discord.Interaction):
        if not interaction.channel or not interaction.guild:
            await interaction.response.send_message(
                "Use in a server channel.", ephemeral=True
            )
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

        if not player.alive:
            await interaction.response.send_message("You are dead!", ephemeral=True)
            return

        if player.role != "Impostor":
            await interaction.response.send_message(
                "Only impostors can sabotage!", ephemeral=True
            )
            return

        if game.phase != "tasks":
            await interaction.response.send_message(
                f"Cannot sabotage during {game.phase}!", ephemeral=True
            )
            return

        if hasattr(game, "active_sabotage") and game.active_sabotage:
            await interaction.response.send_message(
                f"Sabotage already active: {game.active_sabotage}", ephemeral=True
            )
            return

        if player.sabotage_cooldown > 0:
            await interaction.response.send_message(
                f"⏳ Sabotage on cooldown! {player.sabotage_cooldown}s remaining",
                ephemeral=True,
            )
            return

        view = SabotageView(game, cast(discord.TextChannel, interaction.channel), self.bot)
        await interaction.response.send_message(
            "🔧 **Select a sabotage:**", view=view, ephemeral=True
        )

    @app_commands.command(name="fixsabotage", description="Fix an active sabotage")
    @app_commands.describe(sabotage_type="The type of sabotage to fix")
    @app_commands.choices(
        sabotage_type=[
            app_commands.Choice(name="Electrical", value="electrical"),
            app_commands.Choice(name="O2", value="o2"),
            app_commands.Choice(name="Communications", value="communications"),
            app_commands.Choice(name="Doors", value="doors"),
            app_commands.Choice(name="Reactor", value="reactor"),
        ]
    )
    async def fixsabotage(self, interaction: discord.Interaction, sabotage_type: str):
        if not interaction.channel:
            await interaction.response.send_message(
                "Use in a server channel.", ephemeral=True
            )
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

        if not player.alive:
            await interaction.response.send_message("You are dead!", ephemeral=True)
            return

        active_sabotage = getattr(game, "active_sabotage", None)
        if not active_sabotage:
            await interaction.response.send_message(
                f"No sabotage is currently active!", ephemeral=True
            )
            return

        if active_sabotage.lower() != sabotage_type.lower():
            await interaction.response.send_message(
                f"No {sabotage_type} sabotage active! Current sabotage: {active_sabotage}", ephemeral=True
            )
            return

        view = FixSabotageView(
            sabotage_type, game, cast(discord.TextChannel, interaction.channel), player
        )

        bonus_text = ""
        if player.role == 'Engineer':
            fix_time = 20.0 / player.sabotage_fix_speed
            bonus_text = f"\n⚙️ *Engineer bonus: {fix_time:.0f}s instead of 20s!*"
        
        await interaction.response.send_message(
            f"🔧 **Fixing {sabotage_type}...**\nClick both buttons to fix!{bonus_text}",
            view=view,
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(SabotageCog(bot))
