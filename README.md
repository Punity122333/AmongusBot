# AmongUsBot

AmongUsBot is a Discord game bot that implements an Among Us-like experience inside a server. The bot supports human players and AI bots, impostor mechanics, sabotages, meetings, tasks, and map rendering.

## Features

- Play Among Us style games inside a Discord server
- Support for human players and bot players
- Impostor mechanics with kill cooldowns and vents
- Sabotages and fix-sabotage interactions
- Task system for crewmates and bot-driven task behavior
- Map rendering utilities and a test for map rendering

## Requirements

- Python 3.12
- A Discord bot token with application commands enabled

## Installation

1. Clone the repository.
2. Create and activate a virtual environment:

   python -m venv .venv
   source .venv/bin/activate

3. Install dependencies:

   pip install -r requirements.txt

4. Configure environment variables. Create a `.env` file or export the variables in your shell. At minimum set:

   DISCORD_TOKEN=<your-bot-token>

Optionally set other configuration values depending on how you host the bot.

## Running the bot

With the virtual environment active and dependencies installed, run:

   python main.py

The bot will register application (slash) commands with Discord and connect to the configured guilds.

## Common commands

The bot exposes several application commands (slash commands). Examples include:

- `/start` or `/startgame` to initialize a game (check the actual command names implemented in the cogs)
- `/join` and `/leave` to manage player participation
- `/kill` and `/killcooldown` for impostor kill actions
- `/map` to render the current map
- `/reportbody` to call meetings when a body is found
- `/fixsabotage` to resolve active sabotages
- `/vent` to use vents as an impostor
- `/status` to check game status
- `/end` to force-end a game

Command names and options are defined inside the `cogs/commands` folder.

## Development

- Project source is under the `cogs/` and `amongus/` folders.
- Background game loops and bot AI behavior are implemented in `cogs/commands/game_loops.py`.
- Map rendering utilities are in `amongus/map_renderer.py` and a basic test is available at `test_map_rendering.py`.

Run the test suite with pytest:

   pytest -q

## Contributing

Contributions are welcome. Open issues for bugs or feature requests and submit pull requests for changes.

## License

This project does not include a license file. Add a license that fits your needs if you intend to publish or distribute the code.
