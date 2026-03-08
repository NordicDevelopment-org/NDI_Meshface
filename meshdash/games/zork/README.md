This folder contains the current peer-to-peer text adventure used by the bot.

Files:

- `world.py`: room layout and item placement.
- `engine.py`: command parsing, session state, and game rules.
- `port_tools/extract_upstream_rooms.py`: helper that extracts room data from the original MDL source.
- `upstream_1977/extracted_rooms.json`: generated structured room data from the upstream source.
- `upstream_1977/zork-master/`: original 1977 MIT Zork MDL source and archival files.

Important:

- The current Python bot app is still a simplified playable example.
- The files under `upstream_1977/zork-master/` are reference source, not directly executable by Meshyface.
- A true "full game" port means translating the MDL game logic into this Python bot-app structure.
- The extracted room data currently covers `144` rooms, but that data is not wired into the live game yet.

If you need to regenerate the extracted room data:

```bash
python -m meshdash.games.zork.port_tools.extract_upstream_rooms
```

To make your own game, the fastest path is:

1. Duplicate this folder.
2. Rename the class and `SPEC` metadata in `engine.py`.
3. Rewrite `world.py` to match your map.
4. Adjust `engine.py` for any new verbs, puzzles, or win conditions.
5. Register your copied app in `meshdash/bot_apps/registry.py`.

The bot only provides message routing, settings, and request logging. The app logic stays here.

For the built-in Zork example specifically, the porting path is:

1. Use `upstream_1977/zork-master/` as the authoritative game reference.
2. Start from `upstream_1977/extracted_rooms.json` for the room graph.
3. Expand `world.py` into a much larger data set of rooms, objects, and state.
4. Grow `engine.py` from a tiny demo parser into a more complete adventure engine.
5. Port puzzles and verbs incrementally, testing them in the bot shell as you go.
