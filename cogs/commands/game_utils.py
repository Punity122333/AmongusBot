"""Utility functions for game logic"""

import discord


async def cleanup_game(game, bot=None):
    """
    Cleanup a game from both database and cache.
    Properly removes the game from everywhere when it ends.
    """
    try:
        channel_id = game.channel_id
        
        # Try to get game_manager from the bot or from game's db
        game_manager = None
        
        # Method 1: Try to get from bot
        if bot and hasattr(bot, 'game_manager'):
            game_manager = bot.game_manager
        
        # Method 2: Try to get from game's db
        elif hasattr(game, 'db') and game.db:
            # Import here to avoid circular imports
            from amongus.game_manager import GameManager
            # The game manager should be accessible through the bot
            # but we can also create a temporary one if needed
            if bot and hasattr(bot, 'amongus_games'):
                # Find game manager by checking if it has the same cache
                if hasattr(bot, 'game_manager'):
                    game_manager = bot.game_manager
        
        # Method 3: Try to access via the games dict directly
        if not game_manager and bot and hasattr(bot, 'amongus_games'):
            # Remove from cache directly
            if channel_id in bot.amongus_games:
                del bot.amongus_games[channel_id]
                print(f'✅ Removed game from cache for channel {channel_id}')
        
        # Use game manager if available (preferred method)
        if game_manager:
            await game_manager.delete_game(channel_id)
            print(f'✅ Deleted game via game_manager for channel {channel_id}')
        # Fallback: delete from database directly
        elif hasattr(game, 'db') and game.db:
            await game.db.delete_game(channel_id)
            print(f'✅ Deleted game from database for channel {channel_id}')
            
    except Exception as e:
        print(f'⚠️  Error cleaning up game: {e}')


async def check_and_announce_winner(
    game, channel: discord.TextChannel, context: str = "", bot=None
) -> bool:
    """
    Check win condition and announce if there's a winner.
    Returns True if game ended, False otherwise.
    Prevents duplicate win announcements.
    Also removes the game from the database and cache when the game ends.
    """
    if game.phase == "ended":
        return True

    winner = game.check_win()
    if winner:
        # Cancel all background tasks immediately
        if hasattr(game, 'cancel_all_tasks'):
            game.cancel_all_tasks()
        
        # Clear any active sabotages
        game.active_sabotage = None
        
        game.phase = "ended"

        if winner == "crewmates":
            message = "🎉 **CREWMATES WIN!** 🎉\n"
            if "task" in context.lower():
                message += "All tasks have been completed!"
            elif "impostor" in context.lower():
                message += "All impostors eliminated!"
            else:
                message += "All tasks completed or all impostors eliminated!"
            message += "\n\n🛑 Game has ended. Use `/create` to start a new lobby."
        else:
            message = "💀 **IMPOSTORS WIN!** 💀\n"
            if "kill" in context.lower():
                message += "Impostors have eliminated enough crewmates!"
            elif "sabotage" in context.lower():
                message += context
            else:
                message += "Impostors have taken over the ship!"
            message += "\n\n🛑 Game has ended. Use `/create` to start a new lobby."

        await channel.send(message)
        
        # Clean up game from everywhere
        await cleanup_game(game, bot)
        
        return True

    return False
