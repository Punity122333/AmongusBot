from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from typing import Dict, List, Optional, Tuple
import random


class Room:
    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        width: int = 80,
        height: int = 60,
        connected_rooms: Optional[List[str]] = None,
        has_tasks: bool = True,
        task_list: Optional[List[str]] = None,
        can_vent: bool = False,
    ):
        self.name = name
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.connected_rooms = connected_rooms or []
        self.has_tasks = has_tasks
        self.task_list = task_list or []
        self.can_vent = can_vent
        self.bodies: List[str] = []

    def add_connection(self, room_name: str):
        if room_name not in self.connected_rooms:
            self.connected_rooms.append(room_name)

    def add_body(self, player_name: str):
        if player_name not in self.bodies:
            self.bodies.append(player_name)

    def remove_body(self, player_name: str):
        if player_name in self.bodies:
            self.bodies.remove(player_name)

    def clear_bodies(self):
        self.bodies.clear()

    def to_dict(self):
        return {
            'name': self.name,
            'connected_rooms': self.connected_rooms,
            'has_tasks': self.has_tasks,
            'task_list': self.task_list,
            'can_vent': self.can_vent,
            'bodies': self.bodies,
        }


class MapLayout:
    def __init__(self):
        self.rooms: Dict[str, Room] = {}
        self._initialize_skeld_map()

    def _initialize_skeld_map(self):
        room_definitions = [
            ("Cafeteria", 360, 45, 135, 98, ["Weapons", "Upper Engine", "Admin", "MedBay"], True, ["Download Data", "Empty Garbage"], True),
            ("MedBay", 210, 45, 105, 83, ["Upper Engine", "Cafeteria"], True, ["Submit Scan", "Inspect Sample"], True),
            ("Weapons", 675, 45, 113, 83, ["Cafeteria", "O2", "Nav"], True, ["Download Data", "Clear Asteroids"], False),
            ("Upper Engine", 45, 45, 120, 98, ["Reactor", "Security", "Cafeteria", "MedBay"], True, ["Align Engine Output", "Fuel Engines"], True),
            ("Reactor", 45, 180, 113, 90, ["Security", "Upper Engine", "Electrical"], True, ["Start Reactor", "Unlock Manifolds"], True),
            ("Security", 195, 180, 105, 83, ["Electrical", "Reactor", "Upper Engine", "Lower Engine"], True, ["Fix Wiring"], True),
            ("Admin", 360, 180, 105, 83, ["Cafeteria", "Storage", "Hallway"], True, ["Swipe Card", "Upload Data"], True),
            ("Hallway", 495, 203, 130, 80, ["Admin"], False, [], False),
            ("O2", 675, 165, 90, 83, ["Weapons", "Nav", "Shields"], True, ["Monitor Tree", "Clean O2 Filter"], True),
            ("Nav", 795, 165, 90, 83, ["Weapons", "O2", "Shields"], True, ["Chart Course", "Download Data"], True),
            ("Electrical", 45, 315, 128, 90, ["Storage", "Lower Engine", "Security","Reactor"], True, ["Fix Wiring", "Download Data", "Divert Power"], True),
            ("Storage", 360, 315, 128, 98, ["Cafeteria", "Shields", "Communications", "Admin", "Electrical"], True, ["Fuel Engines", "Empty Garbage"], True),
            ("Shields", 675, 315, 105, 83, ["Nav", "O2", "Storage", "Communications"], True, ["Prime Shields"], True),
            ("Lower Engine", 45, 443, 128, 98, ["Security", "Electrical"], True, ["Align Engine Output", "Fuel Engines"], True),
            ("Communications", 540, 443, 128, 90, ["Shields", "Storage"], True, ["Download Data"], True),
        ]

        for room_data in room_definitions:
            name, x, y, w, h, connections, has_tasks, tasks, can_vent = room_data
            room = Room(name, x, y, w, h, connections, has_tasks, tasks, can_vent)
            self.rooms[name] = room

    def get_room(self, room_name: str) -> Optional[Room]:
        return self.rooms.get(room_name)

    def is_connected(self, room1: str, room2: str) -> bool:
        room = self.get_room(room1)
        if room:
            return room2 in room.connected_rooms
        return False

    def add_body_to_room(self, room_name: str, player_name: str):
        room = self.get_room(room_name)
        if room:
            room.add_body(player_name)

    def remove_body_from_room(self, room_name: str, player_name: str):
        room = self.get_room(room_name)
        if room:
            room.remove_body(player_name)

    def clear_all_bodies(self):
        for room in self.rooms.values():
            room.clear_bodies()


class MapRenderer:
    def __init__(self, map_layout: MapLayout, width: int = 923, height: int = 600):
        self.map_layout = map_layout
        self.width = width
        self.height = height
        self.bg_color = (20, 20, 40)
        self.room_color = (60, 60, 80)
        self.room_border = (100, 100, 120)
        self.player_room_color = (50, 200, 50)
        self.sabotage_color = (220, 50, 50)
        self.text_color = (255, 255, 255)
        self.connection_color = (80, 80, 100)

    def _draw_stars(self, draw: ImageDraw.ImageDraw):
        random.seed(42)
        for _ in range(120):
            x = random.randint(0, self.width)
            y = random.randint(0, self.height)
            size = random.choice([1, 1, 1, 2, 3])
            brightness = random.randint(180, 255)
            color = (brightness, brightness, brightness)
            if size == 1:
                draw.point((x, y), fill=color)
            else:
                draw.ellipse([x-size//2, y-size//2, x+size//2, y+size//2], fill=color)

    def _draw_connections(self, draw: ImageDraw.ImageDraw):
        drawn_connections = set()
        for room in self.map_layout.rooms.values():
            for connected_name in room.connected_rooms:
                connection_key = tuple(sorted([room.name, connected_name]))
                if connection_key in drawn_connections:
                    continue
                drawn_connections.add(connection_key)
                
                connected_room = self.map_layout.get_room(connected_name)
                if connected_room:
                    x1 = room.x + room.width // 2
                    y1 = room.y + room.height // 2
                    x2 = connected_room.x + connected_room.width // 2
                    y2 = connected_room.y + connected_room.height // 2
                    draw.line([(x1, y1), (x2, y2)], fill=self.connection_color, width=3)

    def _draw_room(
        self,
        draw: ImageDraw.ImageDraw,
        room: Room,
        is_player_room: bool = False,
        is_sabotaged: bool = False,
    ):
        if is_player_room:
            fill_color = self.player_room_color
        elif is_sabotaged:
            fill_color = self.sabotage_color
        else:
            fill_color = self.room_color

        x1, y1 = room.x, room.y
        x2, y2 = room.x + room.width, room.y + room.height
        
        draw.rounded_rectangle(
            [x1, y1, x2, y2],
            radius=12,
            fill=fill_color,
            outline=self.room_border,
            width=3
        )

    def _draw_room_label(self, draw: ImageDraw.ImageDraw, room: Room, font):
        # Use shortened name for Communications on the map
        text = "Comms" if room.name == "Communications" else room.name
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        if room.name in ["Upper Engine", "Lower Engine"]:
            words = text.split()
            line1 = words[0]
            line2 = words[1]
            
            bbox1 = draw.textbbox((0, 0), line1, font=font)
            bbox2 = draw.textbbox((0, 0), line2, font=font)
            text_width1 = bbox1[2] - bbox1[0]
            text_width2 = bbox2[2] - bbox2[0]
            text_height1 = bbox1[3] - bbox1[1]
            
            text_x1 = room.x + (room.width - text_width1) // 2
            text_y1 = room.y + (room.height - text_height1 * 2 - 2) // 2
            text_x2 = room.x + (room.width - text_width2) // 2
            text_y2 = text_y1 + text_height1 + 2
            
            draw.text((text_x1, text_y1), line1, fill=self.text_color, font=font)
            draw.text((text_x2, text_y2), line2, fill=self.text_color, font=font)
        elif text_width > room.width - 12:
            words = text.split()
            if len(words) > 1:
                line1 = words[0]
                line2 = ' '.join(words[1:])
                
                bbox1 = draw.textbbox((0, 0), line1, font=font)
                bbox2 = draw.textbbox((0, 0), line2, font=font)
                text_width1 = bbox1[2] - bbox1[0]
                text_width2 = bbox2[2] - bbox2[0]
                text_height1 = bbox1[3] - bbox1[1]
                
                text_x1 = room.x + (room.width - text_width1) // 2
                text_y1 = room.y + (room.height - text_height1 * 2 - 2) // 2
                text_x2 = room.x + (room.width - text_width2) // 2
                text_y2 = text_y1 + text_height1 + 2
                
                draw.text((text_x1, text_y1), line1, fill=self.text_color, font=font)
                draw.text((text_x2, text_y2), line2, fill=self.text_color, font=font)
            else:
                smaller_font = ImageFont.load_default()
                bbox = draw.textbbox((0, 0), text, font=smaller_font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                text_x = room.x + (room.width - text_width) // 2
                text_y = room.y + (room.height - text_height) // 2
                draw.text((text_x, text_y), text, fill=self.text_color, font=smaller_font)
        else:
            text_x = room.x + (room.width - text_width) // 2
            text_y = room.y + (room.height - text_height) // 2
            draw.text((text_x, text_y), text, fill=self.text_color, font=font)

    def _draw_skull(self, draw: ImageDraw.ImageDraw, room: Room):
        center_x = room.x + room.width - 23
        center_y = room.y + 15
        
        draw.ellipse(
            [center_x - 9, center_y - 9, center_x + 9, center_y + 9],
            fill=(255, 255, 255),
            outline=(0, 0, 0),
            width=2
        )
        
        draw.ellipse([center_x - 6, center_y - 5, center_x - 3, center_y - 2], fill=(0, 0, 0))
        draw.ellipse([center_x + 3, center_y - 5, center_x + 6, center_y - 2], fill=(0, 0, 0))
        
        draw.line([(center_x - 3, center_y + 3), (center_x + 3, center_y + 3)], fill=(0, 0, 0), width=2)

    def render(
        self,
        player_room: Optional[str] = None,
        sabotaged_rooms: Optional[List[str]] = None,
    ) -> BytesIO:
        sabotaged_rooms = sabotaged_rooms or []
        
        img = Image.new('RGB', (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(img)
        
        self._draw_stars(draw)
        
        self._draw_connections(draw)
        
        try:
            font = ImageFont.truetype("../fonts/DejaVuSans-Bold.ttf", 19)
        except:
            try:
                font = ImageFont.truetype("../fonts/Helvetica-Bold.ttf", 19)
            except:
                font = ImageFont.load_default()
        
        for room in self.map_layout.rooms.values():
            is_player = room.name == player_room
            is_sabotaged = room.name in sabotaged_rooms
            self._draw_room(draw, room, is_player, is_sabotaged)
        
        for room in self.map_layout.rooms.values():
            self._draw_room_label(draw, room, font)
        
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer


class VentMapRenderer:
    """Renderer for vent system map"""
    def __init__(self, map_layout: MapLayout, width: int = 923, height: int = 600):
        self.map_layout = map_layout
        self.width = width
        self.height = height
        self.bg_color = (15, 15, 35)
        self.vent_color = (60, 60, 80)
        self.vent_highlight_color = (255, 50, 50)
        self.vent_border = (100, 100, 120)
        self.connection_color = (80, 255, 80)
        
        # Vent connections network (rooms that can be connected via vents)
        self.vent_connections = {
            "Cafeteria": ["Admin", "MedBay"],
            "Upper Engine": ["Reactor", "Security"],
            "Reactor": ["Upper Engine", "Security", "Electrical"],
            "Security": ["Upper Engine", "Reactor", "Electrical", "Lower Engine", "Storage"],
            "Lower Engine": ["Security", "Electrical"],
            "Electrical": ["Security", "MedBay", "Reactor", "Lower Engine"],
            "MedBay": ["Electrical", "Cafeteria"],
            "Admin": ["Cafeteria", "O2"],
            "O2": ["Admin", "Nav", "Shields"],
            "Nav": ["O2", "Shields"],
            "Shields": ["O2", "Nav", "Communications"],
            "Storage": ["Admin", "Communications", "Security"],
            "Communications": ["Shields", "Storage"],
        }

    def _draw_stars(self, draw: ImageDraw.ImageDraw):
        """Draw background stars"""
        random.seed(42)
        for _ in range(100):
            x = random.randint(0, self.width)
            y = random.randint(0, self.height)
            size = random.randint(1, 2)
            draw.ellipse([x, y, x + size, y + size], fill=(200, 200, 220))

    def _draw_vent_connections(self, draw: ImageDraw.ImageDraw):
        """Draw vent tunnel connections"""
        drawn = set()
        for room_name, connections in self.vent_connections.items():
            room = self.map_layout.get_room(room_name)
            if not room or not room.can_vent:
                continue
                
            for connected_room_name in connections:
                connected = self.map_layout.get_room(connected_room_name)
                if not connected or not connected.can_vent:
                    continue
                
                # Avoid drawing the same line twice
                key = tuple(sorted([room_name, connected_room_name]))
                if key in drawn:
                    continue
                drawn.add(key)
                
                x1 = room.x + room.width // 2
                y1 = room.y + room.height // 2
                x2 = connected.x + connected.width // 2
                y2 = connected.y + connected.height // 2
                
                # Draw dashed line for vent tunnel
                draw.line([x1, y1, x2, y2], fill=self.connection_color, width=3)

    def _draw_vent(self, draw: ImageDraw.ImageDraw, room: Room, is_player_vent: bool = False):
        """Draw a vent entrance"""
        if not room.can_vent:
            return
            
        fill_color = self.vent_highlight_color if is_player_vent else self.vent_color
        
        x1, y1 = room.x, room.y
        x2, y2 = room.x + room.width, room.y + room.height
        
        # Draw vent entrance as rounded rectangle
        draw.rounded_rectangle(
            [x1, y1, x2, y2],
            radius=12,
            fill=fill_color,
            outline=self.vent_border,
            width=4 if is_player_vent else 3
        )
        

    def _draw_vent_label(self, draw: ImageDraw.ImageDraw, room: Room, font):
        """Draw vent room label"""
        if not room.can_vent:
            return
            
        text = f"{room.name}" if room.name != "Communications" else "Comms"
        text = text if room.name != "Upper Engine" and room.name != "Lower Engine" else text.replace("Engine", "\nEng")

        
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        text_x = room.x + (room.width - text_width) // 2
        text_y = room.y + (room.height - text_height) // 2
        
        # Draw text shadow
        draw.text((text_x + 1, text_y + 1), text, font=font, fill=(0, 0, 0))
        # Draw main text
        draw.text((text_x, text_y), text, font=font, fill=(255, 255, 255))

    def render(self, player_vent: Optional[str] = None) -> BytesIO:
        """Render the vent map"""
        img = Image.new('RGB', (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(img)
        
        self._draw_stars(draw)
        self._draw_vent_connections(draw)
        
        try:
            font = ImageFont.truetype("fonts/DejaVuSans-Bold.ttf", 18)
        except:
            try:
                font = ImageFont.truetype("fonts/Helvetica-Bold.ttf", 18)
            except:
                font = ImageFont.load_default()
        
        # Draw all vents
        for room in self.map_layout.rooms.values():
            if room.can_vent:
                is_player = room.name == player_vent
                self._draw_vent(draw, room, is_player)
        
        # Draw vent labels
        for room in self.map_layout.rooms.values():
            if room.can_vent:
                self._draw_vent_label(draw, room, font)
        
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer


def create_map_image(
    player_room: Optional[str] = None,
    sabotaged_rooms: Optional[List[str]] = None,
    map_layout: Optional[MapLayout] = None,
) -> BytesIO:
    if map_layout is None:
        map_layout = MapLayout()
    
    renderer = MapRenderer(map_layout)
    return renderer.render(player_room, sabotaged_rooms)


def create_vent_map_image(
    player_vent: Optional[str] = None,
    map_layout: Optional[MapLayout] = None,
) -> BytesIO:
    """Create a vent-only map showing vent connections"""
    if map_layout is None:
        map_layout = MapLayout()
    renderer = VentMapRenderer(map_layout)
    return renderer.render(player_vent)


