This folder contains the current peer-to-peer text adventure used by the bot.

Files:

- `world.py`: room layout and item placement.
- `engine.py`: command parsing, session state, and game rules.

To make your own game, the fastest path is:

1. Duplicate this folder.
2. Rename the class and `SPEC` metadata in `engine.py`.
3. Rewrite `world.py` to match your map.
4. Adjust `engine.py` for any new verbs, puzzles, or win conditions.
5. Register your copied app in `meshdash/bot_apps/registry.py`.

The bot only provides message routing, settings, and request logging. The app logic stays here.
