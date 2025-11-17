"""Card generation using Pillow for player cards, role reveals, etc."""
import io
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import aiohttp
from typing import Optional
from .constants import (
    CARD_WIDTH, CARD_HEIGHT, AVATAR_SIZE,
    ROLE_CARD_WIDTH, ROLE_CARD_HEIGHT,
    LOBBY_CARD_WIDTH, LOBBY_CARD_HEIGHT,
    PLAYER_COLORS
)


async def download_avatar(url: str) -> Optional[Image.Image]:
    """Download and return avatar image"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    return Image.open(io.BytesIO(data)).convert('RGBA')
    except Exception as e:
        print(f"Failed to download avatar: {e}")
    return None


def get_font(size: int, bold: bool = False):
    """Get font, fallback to default if custom not available"""
    try:
        if bold:
            return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except:
        return ImageFont.load_default()


async def create_player_card(player_name: str, avatar_url: str, color: str, role: str, alive: bool = True) -> io.BytesIO:
    """Create a player card with avatar and info"""
    # Create base image
    img = Image.new('RGBA', (CARD_WIDTH, CARD_HEIGHT), color=(30, 30, 40, 255))
    draw = ImageDraw.Draw(img)
    
    # Download and process avatar
    avatar = await download_avatar(avatar_url)
    if avatar:
        # Resize and make circular
        avatar = avatar.resize((AVATAR_SIZE, AVATAR_SIZE), Image.Resampling.LANCZOS)
        
        # Create circular mask
        mask = Image.new('L', (AVATAR_SIZE, AVATAR_SIZE), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, AVATAR_SIZE, AVATAR_SIZE), fill=255)
        
        # Apply mask
        avatar.putalpha(mask)
        
        # Add border
        border_size = 10
        bordered = Image.new('RGBA', (AVATAR_SIZE + border_size*2, AVATAR_SIZE + border_size*2), color)
        bordered_draw = ImageDraw.Draw(bordered)
        bordered_draw.ellipse((0, 0, AVATAR_SIZE + border_size*2, AVATAR_SIZE + border_size*2), fill=color)
        bordered.paste(avatar, (border_size, border_size), avatar)
        
        # Paste avatar on card
        img.paste(bordered, (CARD_WIDTH//2 - (AVATAR_SIZE + border_size*2)//2, 100), bordered)
    
    # Draw player name
    name_font = get_font(40, bold=True)
    name_bbox = draw.textbbox((0, 0), player_name, font=name_font)
    name_width = name_bbox[2] - name_bbox[0]
    draw.text((CARD_WIDTH//2 - name_width//2, 500), player_name, fill=(255, 255, 255), font=name_font)
    
    # Draw role
    role_font = get_font(50, bold=True)
    role_color = (255, 50, 50) if role == 'Impostor' else (100, 200, 255)
    role_bbox = draw.textbbox((0, 0), role, font=role_font)
    role_width = role_bbox[2] - role_bbox[0]
    draw.text((CARD_WIDTH//2 - role_width//2, 600), role, fill=role_color, font=role_font)
    
    # Draw alive/dead status
    if not alive:
        status_font = get_font(35, bold=True)
        status_text = "DEAD"
        status_bbox = draw.textbbox((0, 0), status_text, font=status_font)
        status_width = status_bbox[2] - status_bbox[0]
        draw.text((CARD_WIDTH//2 - status_width//2, 750), status_text, fill=(200, 50, 50), font=status_font)
    
    # Draw decorative elements
    draw.rectangle((50, 50, CARD_WIDTH-50, CARD_HEIGHT-50), outline=color, width=5)
    
    # Save to BytesIO
    buffer = io.BytesIO()
    img.save(buffer, 'PNG')
    buffer.seek(0)
    return buffer


async def create_role_reveal_card(player_name: str, role: str, task_count: int = 0, avatar_url: str = "") -> io.BytesIO:
    """Create a dramatic role reveal card"""
    img = Image.new('RGBA', (ROLE_CARD_WIDTH, ROLE_CARD_HEIGHT), color=(20, 20, 30, 255))
    draw = ImageDraw.Draw(img)
    
    if role == 'Impostor':
        bg_color = (100, 20, 20, 200)
        text_color = (255, 100, 100)
        role_emoji = "🔪"
        mission_text = "Eliminate all crewmates to win!"
        details = [
            "• Use /kill to eliminate crewmates",
            "• Use /sabotage to create chaos",
            "• Use /vent to move quickly",
            "• Fake tasks to blend in"
        ]
    elif role == 'Scientist':
        bg_color = (20, 80, 120, 200)
        text_color = (100, 220, 255)
        role_emoji = "🧪"
        mission_text = f"Complete {task_count} tasks faster!"
        details = [
            "• Task completion speed: 1.5x",
            "• Use /tasks to view your task list",
            "• Use /dotask to complete tasks",
            "• Help the crew win quickly"
        ]
    elif role == 'Engineer':
        bg_color = (80, 60, 20, 200)
        text_color = (255, 200, 100)
        role_emoji = "🔧"
        mission_text = f"Complete {task_count} tasks & use vents!"
        details = [
            "• Can use vents like impostors",
            "• Sabotage fix speed: 2x",
            "• Use /vent to move through vents",
            "• Complete tasks to help crew"
        ]
    else:
        bg_color = (20, 50, 100, 200)
        text_color = (100, 200, 255)
        role_emoji = "👷"
        mission_text = f"Complete all {task_count} tasks!"
        details = [
            "• Use /tasks to view your task list",
            "• Use /dotask to complete tasks",
            "• Watch for suspicious behavior",
            "• Report bodies and vote wisely"
        ]
    
    for i in range(ROLE_CARD_HEIGHT):
        alpha = int(255 * (i / ROLE_CARD_HEIGHT))
        color = (*bg_color[:3], min(alpha, bg_color[3]))
        draw.rectangle((0, i, ROLE_CARD_WIDTH, i+1), fill=color)
    
    title_font = get_font(70, bold=True)
    title_text = role.upper()
    title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    draw.text((ROLE_CARD_WIDTH//2 - title_width//2, 50), title_text, fill=text_color, font=title_font)
    
    avatar = await download_avatar(avatar_url)
    if avatar:
        avatar_size = 150
        avatar = avatar.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
        
        mask = Image.new('L', (avatar_size, avatar_size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
        avatar.putalpha(mask)
        
        img.paste(avatar, (ROLE_CARD_WIDTH//2 - avatar_size//2, 170), avatar)
    
    
    desc_font = get_font(28)
    y = 440
    draw.text((ROLE_CARD_WIDTH//2 - draw.textbbox((0, 0), mission_text, font=desc_font)[2]//2, y), mission_text, fill=(255, 255, 255), font=desc_font)
    y += 50
    
    for line in details:
        bbox = draw.textbbox((0, 0), line, font=desc_font)
        width = bbox[2] - bbox[0]
        draw.text((ROLE_CARD_WIDTH//2 - width//2, y), line, fill=(200, 220, 255), font=desc_font)
        y += 35
    
    buffer = io.BytesIO()
    img.save(buffer, 'PNG')
    buffer.seek(0)
    return buffer


async def create_lobby_card(players: list, game_code: str = "ABCDEF") -> io.BytesIO:
    """Create a lobby overview card"""
    height = max(LOBBY_CARD_HEIGHT, 200 + len(players) * 80)
    img = Image.new('RGBA', (LOBBY_CARD_WIDTH, height), color=(25, 30, 45, 255))
    draw = ImageDraw.Draw(img)
    
    # Title
    title_font = get_font(50, bold=True)
    title_text = "AMONG US LOBBY"
    title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    draw.text((LOBBY_CARD_WIDTH//2 - title_width//2, 30), title_text, fill=(100, 200, 255), font=title_font)
    
    # Game code
    code_font = get_font(30)
    code_text = f"Code: {game_code}"
    code_bbox = draw.textbbox((0, 0), code_text, font=code_font)
    code_width = code_bbox[2] - code_bbox[0]
    draw.text((LOBBY_CARD_WIDTH//2 - code_width//2, 120), code_text, fill=(200, 200, 200), font=code_font)
    
    # Player list
    player_font = get_font(28)
    y_offset = 200
    
    for i, player in enumerate(players):
        color = PLAYER_COLORS[i % len(PLAYER_COLORS)]
        
        # Draw color indicator
        draw.ellipse((50, y_offset, 90, y_offset + 40), fill=color)
        
        # Draw player name
        name = player.get('name', 'Unknown')
        is_bot = player.get('is_bot', False)
        bot_tag = " [BOT]" if is_bot else ""
        
        draw.text((110, y_offset), f"{name}{bot_tag}", fill=(255, 255, 255), font=player_font)
        
        y_offset += 70
    
    # Player count
    count_font = get_font(30)
    count_text = f"Players: {len(players)}/10"
    draw.text((50, height - 60), count_text, fill=(150, 150, 150), font=count_font)
    
    # Border
    draw.rectangle((10, 10, LOBBY_CARD_WIDTH-10, height-10), outline=(100, 200, 255), width=5)
    
    # Save to BytesIO
    buffer = io.BytesIO()
    img.save(buffer, 'PNG')
    buffer.seek(0)
    return buffer


async def create_alive_players_card(players: list, game_code: str = "ABCDEF") -> io.BytesIO:
    """Create an alive players overview card (similar to lobby card)"""
    height = max(LOBBY_CARD_HEIGHT, 200 + len(players) * 80)
    img = Image.new('RGBA', (LOBBY_CARD_WIDTH, height), color=(25, 45, 30, 255))
    draw = ImageDraw.Draw(img)
    
    # Title
    title_font = get_font(50, bold=True)
    title_text = "ALIVE PLAYERS"
    title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    draw.text((LOBBY_CARD_WIDTH//2 - title_width//2, 30), title_text, fill=(100, 255, 100), font=title_font)
    
    # Game code
    code_font = get_font(30)
    code_text = f"Code: {game_code}"
    code_bbox = draw.textbbox((0, 0), code_text, font=code_font)
    code_width = code_bbox[2] - code_bbox[0]
    draw.text((LOBBY_CARD_WIDTH//2 - code_width//2, 120), code_text, fill=(200, 200, 200), font=code_font)
    
    # Player list
    player_font = get_font(28)
    y_offset = 200
    
    for i, player in enumerate(players):
        color = player.get('color', PLAYER_COLORS[i % len(PLAYER_COLORS)])
        
        # Draw color indicator
        draw.ellipse((50, y_offset, 90, y_offset + 40), fill=color)
        
        # Draw player name
        name = player.get('name', 'Unknown')
        is_bot = player.get('is_bot', False)
        bot_tag = " [BOT]" if is_bot else ""
        
        role_tag=""
        
        draw.text((110, y_offset), f"{name}{bot_tag}{role_tag}", fill=(255, 255, 255), font=player_font)
        
        y_offset += 70
    
    # Player count
    count_font = get_font(30)
    count_text = f"Alive: {len(players)}"
    draw.text((50, height - 60), count_text, fill=(100, 255, 100), font=count_font)
    
    # Border
    draw.rectangle((10, 10, LOBBY_CARD_WIDTH-10, height-10), outline=(100, 255, 100), width=5)
    
    # Save to BytesIO
    buffer = io.BytesIO()
    img.save(buffer, 'PNG')
    buffer.seek(0)
    return buffer


async def create_emergency_meeting_card(caller_name: Optional[str] = None) -> io.BytesIO:
    """Create emergency meeting card"""
    img = Image.new('RGBA', (ROLE_CARD_WIDTH, ROLE_CARD_HEIGHT), color=(150, 0, 0, 255))
    draw = ImageDraw.Draw(img)
    
    # Pulsing red background effect
    for i in range(0, ROLE_CARD_HEIGHT, 20):
        alpha = int(100 + 155 * abs((i / ROLE_CARD_HEIGHT) - 0.5))
        draw.rectangle((0, i, ROLE_CARD_WIDTH, i+20), fill=(200, 0, 0, alpha))
    
    # Title
    title_font = get_font(70, bold=True)
    title_text = "EMERGENCY MEETING"
    title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    
    # Draw with shadow effect
    shadow_color = (50, 0, 0)
    text_color = (255, 255, 255)
    x = ROLE_CARD_WIDTH//2 - title_width//2
    y = ROLE_CARD_HEIGHT//2 - 80
    
    draw.text((x+5, y+5), title_text, fill=shadow_color, font=title_font)
    draw.text((x, y), title_text, fill=text_color, font=title_font)
    
    # Caller info
    if caller_name:
        caller_font = get_font(40)
        caller_text = f"Called by: {caller_name}"
        caller_bbox = draw.textbbox((0, 0), caller_text, font=caller_font)
        caller_width = caller_bbox[2] - caller_bbox[0]
        draw.text((ROLE_CARD_WIDTH//2 - caller_width//2, ROLE_CARD_HEIGHT//2 + 50), 
                 caller_text, fill=(255, 200, 200), font=caller_font)
    
    # Save to BytesIO
    buffer = io.BytesIO()
    img.save(buffer, 'PNG')
    buffer.seek(0)
    return buffer


async def create_vote_result_card(voted_player: str, votes: int, was_impostor: bool) -> io.BytesIO:
    """Create vote result/ejection card"""
    img = Image.new('RGBA', (ROLE_CARD_WIDTH, ROLE_CARD_HEIGHT), color=(10, 10, 20, 255))
    draw = ImageDraw.Draw(img)
    
    # Background
    bg_color = (100, 20, 20) if was_impostor else (20, 20, 100)
    for i in range(ROLE_CARD_HEIGHT):
        alpha = int(200 - 100 * (i / ROLE_CARD_HEIGHT))
        draw.rectangle((0, i, ROLE_CARD_WIDTH, i+1), fill=(*bg_color, alpha))
    
    # Ejected text
    title_font = get_font(60, bold=True)
    title_text = f"{voted_player} was ejected"
    title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    draw.text((ROLE_CARD_WIDTH//2 - title_width//2, 150), title_text, fill=(255, 255, 255), font=title_font)
    
    # Vote count
    vote_font = get_font(35)
    vote_text = f"{votes} vote(s)"
    vote_bbox = draw.textbbox((0, 0), vote_text, font=vote_font)
    vote_width = vote_bbox[2] - vote_bbox[0]
    draw.text((ROLE_CARD_WIDTH//2 - vote_width//2, 280), vote_text, fill=(200, 200, 200), font=vote_font)
    
    # Role reveal
    role_font = get_font(55, bold=True)
    if was_impostor:
        role_text = "They were an Impostor"
        role_color = (255, 100, 100)
    else:
        role_text = "They were NOT an Impostor"
        role_color = (100, 200, 255)
    
    role_bbox = draw.textbbox((0, 0), role_text, font=role_font)
    role_width = role_bbox[2] - role_bbox[0]
    draw.text((ROLE_CARD_WIDTH//2 - role_width//2, 400), role_text, fill=role_color, font=role_font)
    
    # Save to BytesIO
    buffer = io.BytesIO()
    img.save(buffer, 'PNG')
    buffer.seek(0)
    return buffer



async def create_death_card(player_name: str, avatar_url: str) -> io.BytesIO:
    """Create a death notification card"""
    img = Image.new('RGBA', (ROLE_CARD_WIDTH, ROLE_CARD_HEIGHT), color=(20, 10, 10, 255))
    draw = ImageDraw.Draw(img)
    
    # Dark red background with gradient
    for i in range(ROLE_CARD_HEIGHT):
        alpha = int(150 + 105 * (i / ROLE_CARD_HEIGHT))
        draw.rectangle((0, i, ROLE_CARD_WIDTH, i+1), fill=(80, 0, 0, alpha))
    
    # Download avatar
    avatar = await download_avatar(avatar_url)
    if avatar:
        avatar_size = 200
        avatar = avatar.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
        
        mask = Image.new('L', (avatar_size, avatar_size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
        avatar.putalpha(mask)
        
        
        img.paste(avatar, (ROLE_CARD_WIDTH//2 - avatar_size//2, 100), avatar)
    
    # Death text
    title_font = get_font(70, bold=True)
    title_text = "YOU HAVE BEEN"
    title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    draw.text((ROLE_CARD_WIDTH//2 - title_width//2, 350), title_text, fill=(255, 100, 100), font=title_font)
    
    killed_font = get_font(90, bold=True)
    killed_text = "KILLED!"
    killed_bbox = draw.textbbox((0, 0), killed_text, font=killed_font)
    killed_width = killed_bbox[2] - killed_bbox[0]
    draw.text((ROLE_CARD_WIDTH//2 - killed_width//2, 440), killed_text, fill=(255, 50, 50), font=killed_font)
    
    # Save to BytesIO
    buffer = io.BytesIO()
    img.save(buffer, 'PNG')
    buffer.seek(0)
    return buffer
