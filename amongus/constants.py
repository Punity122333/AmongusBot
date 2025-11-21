MIN_PLAYERS = 4
MAX_PLAYERS = 10
DEFAULT_IMPOSTORS = 1
TASK_COMPLETION_TIME = 10
DISCUSSION_TIME = 60
VOTING_TIME = 30


PLAYER_COLORS = [
    "#C51111",
    "#132ED1",
    "#117F2D",
    "#ED54BA",
    "#EF7D0D",
    "#F5F557",
    "#3F474E",
    "#D6E0F0",
    "#6B2FBB",
    "#71491E",
    "#38FEDC",
    "#50EF39",
]


TASK_TYPES = {
    "wiring": {
        "name": "Fix Wiring",
        "emoji": "⚡",
        "difficulty": "easy",
        "locations": ["Electrical", "Admin", "Nav", "Cafeteria", "Storage", "Security", "Hallway"],
    },
    "download": {
        "name": "Download Data",
        "emoji": "📥",
        "difficulty": "medium",
        "locations": ["Cafeteria", "Nav", "Weapons", "Electrical", "Communications"],
    },
    "fuel": {
        "name": "Fuel Engines",
        "emoji": "⛽",
        "difficulty": "medium",
        "locations": ["Storage", "Upper Engine", "Lower Engine"],
    },
    "trash": {
        "name": "Empty Garbage",
        "emoji": "🗑️",
        "difficulty": "easy",
        "locations": ["Cafeteria", "O2", "Storage"],
    },
    "medbay": {
        "name": "Submit Scan",
        "emoji": "🏥",
        "difficulty": "easy",
        "locations": ["MedBay"],
    },
    "shields": {
        "name": "Prime Shields",
        "emoji": "🛡️",
        "difficulty": "easy",
        "locations": ["Shields"],
    },
    "asteroids": {
        "name": "Clear Asteroids",
        "emoji": "☄️",
        "difficulty": "hard",
        "locations": ["Weapons"],
    },
    "reactor": {
        "name": "Start Reactor",
        "emoji": "⚛️",
        "difficulty": "medium",
        "locations": ["Reactor"],
    },
    "oxygen": {
        "name": "Clean O2 Filter",
        "emoji": "💨",
        "difficulty": "easy",
        "locations": ["O2"],
    },
    "align": {
        "name": "Align Engine Output",
        "emoji": "🔧",
        "difficulty": "medium",
        "locations": ["Upper Engine", "Lower Engine"],
    },
    "calibrate": {
        "name": "Calibrate Distributor",
        "emoji": "🎯",
        "difficulty": "hard",
        "locations": ["Electrical"],
    },
    "chart": {
        "name": "Chart Course",
        "emoji": "🗺️",
        "difficulty": "easy",
        "locations": ["Nav"],
    },
    "divert": {
        "name": "Divert Power",
        "emoji": "🔋",
        "difficulty": "medium",
        "locations": ["Electrical", "Communications", "Nav", "O2", "Weapons", "Shields"],
    },
    "unlock": {
        "name": "Unlock Manifolds",
        "emoji": "🔓",
        "difficulty": "medium",
        "locations": ["Reactor"],
    },
    "inspect": {
        "name": "Inspect Sample",
        "emoji": "🧪",
        "difficulty": "long",
        "locations": ["MedBay"],
    },
    "sort": {
        "name": "Sort Samples",
        "emoji": "📊",
        "difficulty": "easy",
        "locations": ["MedBay"],
    },
    "stabilize": {
        "name": "Stabilize Steering",
        "emoji": "🎮",
        "difficulty": "medium",
        "locations": ["Nav"],
    },
    "storage": {
        "name": "Swipe Card",
        "emoji": "💳",
        "difficulty": "medium",
        "locations": ["Admin"],
    },
    "upload": {
        "name": "Upload Data",
        "emoji": "📤",
        "difficulty": "easy",
        "locations": ["Admin", "Communications"],
    },
    "monitor": {
        "name": "Monitor Security",
        "emoji": "📹",
        "difficulty": "easy",
        "locations": ["Security", "Hallway"],
    },
    "scan": {
        "name": "Run Diagnostics",
        "emoji": "🔬",
        "difficulty": "medium",
        "locations": ["O2", "Nav"],
    },
    "organize": {
        "name": "Organize Storage",
        "emoji": "📦",
        "difficulty": "easy",
        "locations": ["Storage"],
    },
    "adjust": {
        "name": "Adjust Shields",
        "emoji": "⚙️",
        "difficulty": "medium",
        "locations": ["Shields"],
    },
    "repair": {
        "name": "Repair Communications",
        "emoji": "🔧",
        "difficulty": "medium",
        "locations": ["Communications"],
    },
    "calibrate_nav": {
        "name": "Calibrate Navigation",
        "emoji": "🧭",
        "difficulty": "medium",
        "locations": ["Nav"],
    },
    "check_oxygen": {
        "name": "Check Oxygen Levels",
        "emoji": "💨",
        "difficulty": "easy",
        "locations": ["O2"],
    },
}


IMPOSTOR_ACTIONS = {
    "kill": {"name": "Kill", "emoji": "🔪", "cooldown": 25},
    "sabotage": {"name": "Sabotage", "emoji": "💥", "cooldown": 15},
    "vent": {"name": "Vent", "emoji": "🚪", "cooldown": 0},
}


MAP_LOCATIONS = [
    "Cafeteria",
    "Upper Engine",
    "Lower Engine",
    "Security",
    "Reactor",
    "MedBay",
    "Electrical",
    "Storage",
    "Admin",
    "Communications",
    "O2",
    "Nav",
    "Weapons",
    "Shields",
]


CARD_WIDTH = 800
CARD_HEIGHT = 1000
AVATAR_SIZE = 300
ROLE_CARD_WIDTH = 1200
ROLE_CARD_HEIGHT = 675
LOBBY_CARD_WIDTH = 1000
LOBBY_CARD_HEIGHT = 600
