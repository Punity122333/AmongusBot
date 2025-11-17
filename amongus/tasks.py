import discord
from discord import ui
import random
import asyncio
from typing import Optional, Callable
from .constants import TASK_TYPES, TASK_COMPLETION_TIME


class Task:

    def __init__(self, task_type: str, location: str):
        self.task_type = task_type
        self.location = location
        self.task_info = TASK_TYPES[task_type]
        self.completed = False

    @property
    def name(self) -> str:
        return f"{self.task_info['emoji']} {self.task_info['name']} ({self.location })"

    def __str__(self) -> str:
        status = "✅" if self.completed else "⬜"
        return f" {self.name }"


class WiringTaskView(ui.View):

    def __init__(self, on_complete: Callable):
        super().__init__(timeout=TASK_COMPLETION_TIME)
        self.on_complete = on_complete
        self.wires_connected = 0
        self.total_wires = 4

    @ui.button(label="Red Wire", style=discord.ButtonStyle.danger, emoji="🔴")
    async def red_wire(self, interaction: discord.Interaction, button: ui.Button):
        await self._connect_wire(interaction, button, "Red")

    @ui.button(label="Blue Wire", style=discord.ButtonStyle.primary, emoji="🔵")
    async def blue_wire(self, interaction: discord.Interaction, button: ui.Button):
        await self._connect_wire(interaction, button, "Blue")

    @ui.button(label="Yellow Wire", style=discord.ButtonStyle.secondary, emoji="🟡")
    async def yellow_wire(self, interaction: discord.Interaction, button: ui.Button):
        await self._connect_wire(interaction, button, "Yellow")

    @ui.button(label="Green Wire", style=discord.ButtonStyle.success, emoji="🟢")
    async def green_wire(self, interaction: discord.Interaction, button: ui.Button):
        await self._connect_wire(interaction, button, "Green")

    async def _connect_wire(
        self, interaction: discord.Interaction, button: ui.Button, color: str
    ):
        self.wires_connected += 1
        button.disabled = True
        button.label = f"{color } ✓"

        if self.wires_connected >= self.total_wires:
            await interaction.response.edit_message(
                content="⚡ All wires connected! Task complete!", view=self
            )
            self.stop()
            await self.on_complete()
        else:
            await interaction.response.edit_message(
                content=f"⚡ Wire {self.wires_connected }/{self.total_wires } connected...",
                view=self,
            )


class DownloadTaskView(ui.View):

    def __init__(self, on_complete: Callable):
        super().__init__(timeout=TASK_COMPLETION_TIME)
        self.on_complete = on_complete
        self.started = False

    @ui.button(label="Start Download", style=discord.ButtonStyle.primary, emoji="📥")
    async def start_download(self, interaction: discord.Interaction, button: ui.Button):
        if self.started:
            return
        self.started = True
        button.disabled = True
        await interaction.response.edit_message(
            content="📥 Downloading data...", view=self
        )

        for i in range(1, 6):
            await asyncio.sleep(1)
            progress = "█" * i + "░" * (5 - i)
            await interaction.edit_original_response(
                content=f"📥 Downloading: [{progress }] {i *20 }%"
            )

        await interaction.edit_original_response(content="📥 Download complete!")
        self.stop()
        await self.on_complete()


class ShieldsTaskView(ui.View):

    def __init__(self, on_complete: Callable):
        super().__init__(timeout=TASK_COMPLETION_TIME)
        self.on_complete = on_complete
        self.shields_activated = 0
        self.pattern = random.sample(range(9), 4)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return True

    @ui.button(label="1", style=discord.ButtonStyle.secondary, row=0)
    async def shield_1(self, interaction: discord.Interaction, button: ui.Button):
        await self._activate_shield(interaction, button, 0)

    @ui.button(label="2", style=discord.ButtonStyle.secondary, row=0)
    async def shield_2(self, interaction: discord.Interaction, button: ui.Button):
        await self._activate_shield(interaction, button, 1)

    @ui.button(label="3", style=discord.ButtonStyle.secondary, row=0)
    async def shield_3(self, interaction: discord.Interaction, button: ui.Button):
        await self._activate_shield(interaction, button, 2)

    @ui.button(label="4", style=discord.ButtonStyle.secondary, row=1)
    async def shield_4(self, interaction: discord.Interaction, button: ui.Button):
        await self._activate_shield(interaction, button, 3)

    @ui.button(label="5", style=discord.ButtonStyle.secondary, row=1)
    async def shield_5(self, interaction: discord.Interaction, button: ui.Button):
        await self._activate_shield(interaction, button, 4)

    @ui.button(label="6", style=discord.ButtonStyle.secondary, row=1)
    async def shield_6(self, interaction: discord.Interaction, button: ui.Button):
        await self._activate_shield(interaction, button, 5)

    @ui.button(label="7", style=discord.ButtonStyle.secondary, row=2)
    async def shield_7(self, interaction: discord.Interaction, button: ui.Button):
        await self._activate_shield(interaction, button, 6)

    @ui.button(label="8", style=discord.ButtonStyle.secondary, row=2)
    async def shield_8(self, interaction: discord.Interaction, button: ui.Button):
        await self._activate_shield(interaction, button, 7)

    @ui.button(label="9", style=discord.ButtonStyle.secondary, row=2)
    async def shield_9(self, interaction: discord.Interaction, button: ui.Button):
        await self._activate_shield(interaction, button, 8)

    async def _activate_shield(
        self, interaction: discord.Interaction, button: ui.Button, index: int
    ):
        if index in self.pattern:
            self.shields_activated += 1
            button.style = discord.ButtonStyle.success
            button.label = "✓"
            button.disabled = True

            if self.shields_activated >= len(self.pattern):
                await interaction.response.edit_message(
                    content="🛡️ All shields primed! Task complete!", view=self
                )
                self.stop()
                await self.on_complete()
            else:
                await interaction.response.edit_message(
                    content=f"🛡️ Priming shields... {self.shields_activated }/{len(self.pattern )}",
                    view=self,
                )
        else:
            await interaction.response.send_message("❌ Wrong shield!", ephemeral=True)


class AsteroidsTaskView(ui.View):

    def __init__(self, on_complete: Callable):
        super().__init__(timeout=TASK_COMPLETION_TIME)
        self.on_complete = on_complete
        self.asteroids_destroyed = 0
        self.total_asteroids = 20

    @ui.button(label="🎯 FIRE!", style=discord.ButtonStyle.danger, emoji="💥")
    async def fire(self, interaction: discord.Interaction, button: ui.Button):
        self.asteroids_destroyed += random.randint(1, 3)

        if self.asteroids_destroyed >= self.total_asteroids:
            self.asteroids_destroyed = self.total_asteroids
            await interaction.response.edit_message(
                content=f"☄️ All asteroids destroyed! {self.asteroids_destroyed}/{self.total_asteroids} 🎯",
                view=None,
            )
            self.stop()
            await self.on_complete()
        else:
            await interaction.response.edit_message(
                content=f"☄️ Shooting asteroids... {self.asteroids_destroyed}/{self.total_asteroids} destroyed!",
                view=self,
            )


class FuelTaskView(ui.View):
    """Fuel Engines - Fill fuel cans"""

    def __init__(self, on_complete: Callable):
        super().__init__(timeout=TASK_COMPLETION_TIME)
        self.on_complete = on_complete
        self.fuel_level = 0
        self.max_fuel = 100

    @ui.button(label="⛽ Fill Tank", style=discord.ButtonStyle.success, emoji="⛽")
    async def fill_fuel(self, interaction: discord.Interaction, button: ui.Button):
        self.fuel_level += 20
        
        if self.fuel_level >= self.max_fuel:
            self.fuel_level = self.max_fuel
            await interaction.response.edit_message(
                content=f"⛽ Fuel tank full! {self.fuel_level}% - Task complete!",
                view=None,
            )
            self.stop()
            await self.on_complete()
        else:
            progress = "█" * (self.fuel_level // 20) + "░" * (5 - self.fuel_level // 20)
            await interaction.response.edit_message(
                content=f"⛽ Fueling... [{progress}] {self.fuel_level}%",
                view=self,
            )


class TrashTaskView(ui.View):
    """Empty Garbage - Dispose trash"""

    def __init__(self, on_complete: Callable):
        super().__init__(timeout=TASK_COMPLETION_TIME)
        self.on_complete = on_complete
        self.lever_pulled = False

    @ui.button(label="🗑️ Pull Lever", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def pull_lever(self, interaction: discord.Interaction, button: ui.Button):
        if not self.lever_pulled:
            self.lever_pulled = True
            button.disabled = True
            await interaction.response.edit_message(
                content="🗑️ Ejecting trash into space...",
                view=self,
            )
            await asyncio.sleep(2)
            await interaction.edit_original_response(
                content="🗑️ Trash ejected! Task complete!",
                view=None,
            )
            self.stop()
            await self.on_complete()


class MedbayScanTaskView(ui.View):
    """Submit Scan - Medical scan"""

    def __init__(self, on_complete: Callable):
        super().__init__(timeout=TASK_COMPLETION_TIME)
        self.on_complete = on_complete
        self.scanning = False

    @ui.button(label="🏥 Start Scan", style=discord.ButtonStyle.primary, emoji="🏥")
    async def start_scan(self, interaction: discord.Interaction, button: ui.Button):
        if not self.scanning:
            self.scanning = True
            button.disabled = True
            await interaction.response.edit_message(
                content="🏥 Scanning...",
                view=self,
            )
            
            for i in range(1, 6):
                await asyncio.sleep(1)
                await interaction.edit_original_response(
                    content=f"🏥 Scanning... {i * 20}%"
                )
            
            await interaction.edit_original_response(
                content="🏥 Scan complete! You are healthy!",
                view=None,
            )
            self.stop()
            await self.on_complete()


class ReactorTaskView(ui.View):
    """Start Reactor - Simon says pattern"""

    def __init__(self, on_complete: Callable):
        super().__init__(timeout=TASK_COMPLETION_TIME)
        self.on_complete = on_complete
        self.pattern = [random.randint(1, 5) for _ in range(5)]
        self.player_input = []
        self.current_display = 0

    @ui.button(label="1", style=discord.ButtonStyle.primary, row=0)
    async def btn_1(self, interaction: discord.Interaction, button: ui.Button):
        await self._check_pattern(interaction, 1)

    @ui.button(label="2", style=discord.ButtonStyle.primary, row=0)
    async def btn_2(self, interaction: discord.Interaction, button: ui.Button):
        await self._check_pattern(interaction, 2)

    @ui.button(label="3", style=discord.ButtonStyle.primary, row=0)
    async def btn_3(self, interaction: discord.Interaction, button: ui.Button):
        await self._check_pattern(interaction, 3)

    @ui.button(label="4", style=discord.ButtonStyle.primary, row=1)
    async def btn_4(self, interaction: discord.Interaction, button: ui.Button):
        await self._check_pattern(interaction, 4)

    @ui.button(label="5", style=discord.ButtonStyle.primary, row=1)
    async def btn_5(self, interaction: discord.Interaction, button: ui.Button):
        await self._check_pattern(interaction, 5)

    async def _check_pattern(self, interaction: discord.Interaction, number: int):
        self.player_input.append(number)
        
        if self.player_input[-1] != self.pattern[len(self.player_input) - 1]:
            await interaction.response.send_message("❌ Wrong sequence! Try again!", ephemeral=True)
            self.player_input = []
            return
        
        if len(self.player_input) >= len(self.pattern):
            await interaction.response.edit_message(
                content="⚛️ Reactor started! Task complete!",
                view=None,
            )
            self.stop()
            await self.on_complete()
        else:
            await interaction.response.edit_message(
                content=f"⚛️ Sequence progress: {len(self.player_input)}/{len(self.pattern)}",
                view=self,
            )


class OxygenTaskView(ui.View):
    """Clean O2 Filter - Clean the filter"""

    def __init__(self, on_complete: Callable):
        super().__init__(timeout=TASK_COMPLETION_TIME)
        self.on_complete = on_complete
        self.leaves_removed = 0
        self.total_leaves = 6

    @ui.button(label="💨 Remove Leaves", style=discord.ButtonStyle.success, emoji="🍃")
    async def remove_leaves(self, interaction: discord.Interaction, button: ui.Button):
        self.leaves_removed += 1
        
        if self.leaves_removed >= self.total_leaves:
            await interaction.response.edit_message(
                content=f"💨 Filter cleaned! {self.leaves_removed}/{self.total_leaves} leaves removed!",
                view=None,
            )
            self.stop()
            await self.on_complete()
        else:
            await interaction.response.edit_message(
                content=f"💨 Cleaning filter... {self.leaves_removed}/{self.total_leaves} leaves removed",
                view=self,
            )


class AlignEngineTaskView(ui.View):
    """Align Engine Output"""

    def __init__(self, on_complete: Callable):
        super().__init__(timeout=TASK_COMPLETION_TIME)
        self.on_complete = on_complete
        self.aligned = False

    @ui.button(label="🔧 Align Left", style=discord.ButtonStyle.secondary, row=0)
    async def align_left(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("❌ Not aligned!", ephemeral=True)

    @ui.button(label="🔧 Align Center", style=discord.ButtonStyle.success, row=0)
    async def align_center(self, interaction: discord.Interaction, button: ui.Button):
        if not self.aligned:
            self.aligned = True
            await interaction.response.edit_message(
                content="🔧 Engine aligned! Task complete!",
                view=None,
            )
            self.stop()
            await self.on_complete()

    @ui.button(label="🔧 Align Right", style=discord.ButtonStyle.secondary, row=0)
    async def align_right(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("❌ Not aligned!", ephemeral=True)


class CalibrateTaskView(ui.View):
    """Calibrate Distributor - Timing challenge"""

    def __init__(self, on_complete: Callable):
        super().__init__(timeout=TASK_COMPLETION_TIME)
        self.on_complete = on_complete
        self.calibrated = 0
        self.total_calibrations = 3

    @ui.button(label="🎯 Calibrate!", style=discord.ButtonStyle.danger, emoji="⚡")
    async def calibrate(self, interaction: discord.Interaction, button: ui.Button):
        success = random.random() > 0.3  # 70% success rate
        
        if success:
            self.calibrated += 1
            if self.calibrated >= self.total_calibrations:
                await interaction.response.edit_message(
                    content=f"🎯 All calibrations complete! {self.calibrated}/{self.total_calibrations}",
                    view=None,
                )
                self.stop()
                await self.on_complete()
            else:
                await interaction.response.edit_message(
                    content=f"🎯 Calibrating... {self.calibrated}/{self.total_calibrations} done",
                    view=self,
                )
        else:
            await interaction.response.send_message("❌ Missed! Try again!", ephemeral=True)


class ChartCourseTaskView(ui.View):
    """Chart Course - Navigate to waypoints"""

    def __init__(self, on_complete: Callable):
        super().__init__(timeout=TASK_COMPLETION_TIME)
        self.on_complete = on_complete
        self.waypoints = 0
        self.total_waypoints = 4

    @ui.button(label="🗺️ Set Waypoint", style=discord.ButtonStyle.primary, emoji="📍")
    async def set_waypoint(self, interaction: discord.Interaction, button: ui.Button):
        self.waypoints += 1
        
        if self.waypoints >= self.total_waypoints:
            await interaction.response.edit_message(
                content=f"🗺️ Course charted! {self.waypoints}/{self.total_waypoints} waypoints set!",
                view=None,
            )
            self.stop()
            await self.on_complete()
        else:
            await interaction.response.edit_message(
                content=f"🗺️ Charting course... {self.waypoints}/{self.total_waypoints} waypoints",
                view=self,
            )


class DivertPowerTaskView(ui.View):
    """Divert Power - Power routing"""

    def __init__(self, on_complete: Callable):
        super().__init__(timeout=TASK_COMPLETION_TIME)
        self.on_complete = on_complete
        self.diverted = False

    @ui.button(label="🔋 Divert Power", style=discord.ButtonStyle.success, emoji="⚡")
    async def divert(self, interaction: discord.Interaction, button: ui.Button):
        if not self.diverted:
            self.diverted = True
            button.disabled = True
            await interaction.response.edit_message(
                content="🔋 Diverting power...",
                view=self,
            )
            await asyncio.sleep(2)
            await interaction.edit_original_response(
                content="🔋 Power diverted! Task complete!",
                view=None,
            )
            self.stop()
            await self.on_complete()


class UnlockManifoldsTaskView(ui.View):
    """Unlock Manifolds - Spin to unlock"""

    def __init__(self, on_complete: Callable):
        super().__init__(timeout=TASK_COMPLETION_TIME)
        self.on_complete = on_complete
        self.unlocked = 0
        self.total_locks = 10

    @ui.button(label="🔓 Turn Handle", style=discord.ButtonStyle.primary, emoji="🔓")
    async def turn_handle(self, interaction: discord.Interaction, button: ui.Button):
        self.unlocked += 1
        
        if self.unlocked >= self.total_locks:
            await interaction.response.edit_message(
                content=f"🔓 All manifolds unlocked! {self.unlocked}/{self.total_locks}",
                view=None,
            )
            self.stop()
            await self.on_complete()
        else:
            progress = "🔓" * self.unlocked + "🔒" * (self.total_locks - self.unlocked)
            await interaction.response.edit_message(
                content=f"🔓 Unlocking... {progress}",
                view=self,
            )


class InspectSampleTaskView(ui.View):
    """Inspect Sample - Wait for sample analysis"""

    def __init__(self, on_complete: Callable):
        super().__init__(timeout=TASK_COMPLETION_TIME * 6)  # Longer task
        self.on_complete = on_complete
        self.started = False

    @ui.button(label="🧪 Start Analysis", style=discord.ButtonStyle.primary, emoji="🧪")
    async def start_analysis(self, interaction: discord.Interaction, button: ui.Button):
        if not self.started:
            self.started = True
            button.disabled = True
            await interaction.response.edit_message(
                content="🧪 Analyzing sample... This will take 60 seconds.",
                view=self,
            )
            
            await asyncio.sleep(60)
            
            await interaction.edit_original_response(
                content="🧪 Sample analysis complete! No anomalies detected.",
                view=None,
            )
            self.stop()
            await self.on_complete()


class SortSamplesTaskView(ui.View):
    """Sort Samples - Organize samples"""

    def __init__(self, on_complete: Callable):
        super().__init__(timeout=TASK_COMPLETION_TIME)
        self.on_complete = on_complete
        self.sorted_count = 0
        self.total_samples = 4

    @ui.button(label="Red", style=discord.ButtonStyle.danger, emoji="🔴", row=0)
    async def sort_red(self, interaction: discord.Interaction, button: ui.Button):
        await self._sort_sample(interaction, button)

    @ui.button(label="Blue", style=discord.ButtonStyle.primary, emoji="🔵", row=0)
    async def sort_blue(self, interaction: discord.Interaction, button: ui.Button):
        await self._sort_sample(interaction, button)

    @ui.button(label="Green", style=discord.ButtonStyle.success, emoji="🟢", row=1)
    async def sort_green(self, interaction: discord.Interaction, button: ui.Button):
        await self._sort_sample(interaction, button)

    @ui.button(label="Yellow", style=discord.ButtonStyle.secondary, emoji="🟡", row=1)
    async def sort_yellow(self, interaction: discord.Interaction, button: ui.Button):
        await self._sort_sample(interaction, button)

    async def _sort_sample(self, interaction: discord.Interaction, button: ui.Button):
        self.sorted_count += 1
        button.disabled = True
        button.label = "✓"
        
        if self.sorted_count >= self.total_samples:
            await interaction.response.edit_message(
                content=f"📊 All samples sorted! {self.sorted_count}/{self.total_samples}",
                view=self,
            )
            self.stop()
            await self.on_complete()
        else:
            await interaction.response.edit_message(
                content=f"📊 Sorting samples... {self.sorted_count}/{self.total_samples}",
                view=self,
            )


class StabilizeSteeringTaskView(ui.View):
    """Stabilize Steering - Keep crosshair centered"""

    def __init__(self, on_complete: Callable):
        super().__init__(timeout=TASK_COMPLETION_TIME)
        self.on_complete = on_complete
        self.stability = 0
        self.target_stability = 5

    @ui.button(label="🎮 Stabilize", style=discord.ButtonStyle.success, emoji="🎯")
    async def stabilize(self, interaction: discord.Interaction, button: ui.Button):
        self.stability += 1
        
        if self.stability >= self.target_stability:
            await interaction.response.edit_message(
                content=f"🎮 Steering stabilized! {self.stability}/{self.target_stability} adjustments made!",
                view=None,
            )
            self.stop()
            await self.on_complete()
        else:
            await interaction.response.edit_message(
                content=f"🎮 Stabilizing... {self.stability}/{self.target_stability}",
                view=self,
            )


class SwipeCardTaskView(ui.View):
    """Swipe Card - Timing challenge"""

    def __init__(self, on_complete: Callable):
        super().__init__(timeout=TASK_COMPLETION_TIME)
        self.on_complete = on_complete
        self.attempts = 0

    @ui.button(label="💳 Swipe Card", style=discord.ButtonStyle.primary, emoji="💳")
    async def swipe_card(self, interaction: discord.Interaction, button: ui.Button):
        self.attempts += 1
        result = random.choice(["too_fast", "too_slow", "success"])
        
        if result == "success":
            await interaction.response.edit_message(
                content=f"💳 Card accepted! (Attempt {self.attempts})",
                view=None,
            )
            self.stop()
            await self.on_complete()
        elif result == "too_fast":
            await interaction.response.send_message("⚠️ Too fast! Try again.", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Too slow! Try again.", ephemeral=True)


class UploadDataTaskView(ui.View):
    """Upload Data - Upload progress"""

    def __init__(self, on_complete: Callable):
        super().__init__(timeout=TASK_COMPLETION_TIME)
        self.on_complete = on_complete
        self.started = False

    @ui.button(label="📤 Start Upload", style=discord.ButtonStyle.primary, emoji="📤")
    async def start_upload(self, interaction: discord.Interaction, button: ui.Button):
        if not self.started:
            self.started = True
            button.disabled = True
            await interaction.response.edit_message(
                content="📤 Uploading data...",
                view=self,
            )
            
            for i in range(1, 6):
                await asyncio.sleep(1)
                progress = "█" * i + "░" * (5 - i)
                await interaction.edit_original_response(
                    content=f"📤 Uploading: [{progress}] {i * 20}%"
                )
            
            await interaction.edit_original_response(
                content="📤 Upload complete!",
                view=None,
            )
            self.stop()
            await self.on_complete()


class MonitorTaskView(ui.View):

    def __init__(self, on_complete: Callable):
        super().__init__(timeout=TASK_COMPLETION_TIME)
        self.on_complete = on_complete

    @ui.button(label="📹 Check Cameras", style=discord.ButtonStyle.primary, emoji="📹")
    async def check_cameras(self, interaction: discord.Interaction, button: ui.Button):
        button.disabled = True
        await interaction.response.edit_message(
            content="📹 Monitoring security cameras...",
            view=self,
        )
        await asyncio.sleep(3)
        await interaction.edit_original_response(
            content="📹 Security check complete!",
            view=None,
        )
        self.stop()
        await self.on_complete()


class ScanTaskView(ui.View):

    def __init__(self, on_complete: Callable):
        super().__init__(timeout=TASK_COMPLETION_TIME)
        self.on_complete = on_complete

    @ui.button(label="🔬 Start Diagnostics", style=discord.ButtonStyle.primary, emoji="🔬")
    async def start_scan(self, interaction: discord.Interaction, button: ui.Button):
        button.disabled = True
        await interaction.response.edit_message(
            content="🔬 Running diagnostics...",
            view=self,
        )
        await asyncio.sleep(4)
        await interaction.edit_original_response(
            content="🔬 Diagnostics complete!",
            view=None,
        )
        self.stop()
        await self.on_complete()


class OrganizeTaskView(ui.View):

    def __init__(self, on_complete: Callable):
        super().__init__(timeout=TASK_COMPLETION_TIME)
        self.on_complete = on_complete

    @ui.button(label="📦 Organize Items", style=discord.ButtonStyle.primary, emoji="📦")
    async def organize(self, interaction: discord.Interaction, button: ui.Button):
        button.disabled = True
        await interaction.response.edit_message(
            content="📦 Organizing storage...",
            view=self,
        )
        await asyncio.sleep(3)
        await interaction.edit_original_response(
            content="📦 Storage organized!",
            view=None,
        )
        self.stop()
        await self.on_complete()


class AdjustTaskView(ui.View):

    def __init__(self, on_complete: Callable):
        super().__init__(timeout=TASK_COMPLETION_TIME)
        self.on_complete = on_complete

    @ui.button(label="⚙️ Adjust Settings", style=discord.ButtonStyle.primary, emoji="⚙️")
    async def adjust(self, interaction: discord.Interaction, button: ui.Button):
        button.disabled = True
        await interaction.response.edit_message(
            content="⚙️ Adjusting shields...",
            view=self,
        )
        await asyncio.sleep(3)
        await interaction.edit_original_response(
            content="⚙️ Shields adjusted!",
            view=None,
        )
        self.stop()
        await self.on_complete()


class RepairTaskView(ui.View):

    def __init__(self, on_complete: Callable):
        super().__init__(timeout=TASK_COMPLETION_TIME)
        self.on_complete = on_complete

    @ui.button(label="🔧 Repair System", style=discord.ButtonStyle.primary, emoji="🔧")
    async def repair(self, interaction: discord.Interaction, button: ui.Button):
        button.disabled = True
        await interaction.response.edit_message(
            content="🔧 Repairing communications...",
            view=self,
        )
        await asyncio.sleep(4)
        await interaction.edit_original_response(
            content="🔧 Communications repaired!",
            view=None,
        )
        self.stop()
        await self.on_complete()


class CalibrateNavTaskView(ui.View):

    def __init__(self, on_complete: Callable):
        super().__init__(timeout=TASK_COMPLETION_TIME)
        self.on_complete = on_complete

    @ui.button(label="🧭 Calibrate", style=discord.ButtonStyle.primary, emoji="🧭")
    async def calibrate_nav(self, interaction: discord.Interaction, button: ui.Button):
        button.disabled = True
        await interaction.response.edit_message(
            content="🧭 Calibrating navigation...",
            view=self,
        )
        await asyncio.sleep(3)
        await interaction.edit_original_response(
            content="🧭 Navigation calibrated!",
            view=None,
        )
        self.stop()
        await self.on_complete()


class CheckOxygenTaskView(ui.View):

    def __init__(self, on_complete: Callable):
        super().__init__(timeout=TASK_COMPLETION_TIME)
        self.on_complete = on_complete

    @ui.button(label="💨 Check Levels", style=discord.ButtonStyle.primary, emoji="💨")
    async def check_oxygen(self, interaction: discord.Interaction, button: ui.Button):
        button.disabled = True
        await interaction.response.edit_message(
            content="💨 Checking oxygen levels...",
            view=self,
        )
        await asyncio.sleep(2)
        await interaction.edit_original_response(
            content="💨 Oxygen levels normal!",
            view=None,
        )
        self.stop()
        await self.on_complete()


def generate_tasks_for_player(count: Optional[int] = None) -> list[Task]:

    if count is None:
        count = random.randint(7, 8)  # 7-8 tasks per player

    tasks = []
    available_types = list(TASK_TYPES.keys())

    for _ in range(count):
        task_type = random.choice(available_types)
        location = random.choice(TASK_TYPES[task_type]["locations"])
        tasks.append(Task(task_type, location))

    return tasks


def get_task_view(task: Task, on_complete: Callable) -> Optional[ui.View]:
    """Get the interactive view for a task"""
    views = {
        "wiring": WiringTaskView,
        "download": DownloadTaskView,
        "shields": ShieldsTaskView,
        "asteroids": AsteroidsTaskView,
        "fuel": FuelTaskView,
        "trash": TrashTaskView,
        "medbay": MedbayScanTaskView,
        "reactor": ReactorTaskView,
        "oxygen": OxygenTaskView,
        "align": AlignEngineTaskView,
        "calibrate": CalibrateTaskView,
        "chart": ChartCourseTaskView,
        "divert": DivertPowerTaskView,
        "unlock": UnlockManifoldsTaskView,
        "inspect": InspectSampleTaskView,
        "sort": SortSamplesTaskView,
        "stabilize": StabilizeSteeringTaskView,
        "storage": SwipeCardTaskView,
        "upload": UploadDataTaskView,
        "monitor": MonitorTaskView,
        "scan": ScanTaskView,
        "organize": OrganizeTaskView,
        "adjust": AdjustTaskView,
        "repair": RepairTaskView,
        "calibrate_nav": CalibrateNavTaskView,
        "check_oxygen": CheckOxygenTaskView,
    }

    view_class = views.get(task.task_type)
    if view_class:
        return view_class(on_complete)
    return None

