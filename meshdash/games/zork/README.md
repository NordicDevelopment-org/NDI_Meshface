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
- The live game now starts in the classic `West of House` opening and uses the extracted upstream room graph plus parsed upstream object data.
- The current live port supports classic navigation, inventory, reading/examining, mailbox/window/trap-door/grating interactions, lamp/torch/candle lighting, the early troll-room combat path, rope-and-dome traversal, the riddle-room door word, cyclops bypass via the classic magic word, rainbow toggling with the stick, real board/launch/land/disembark river travel with the inflatable boat, the buoy/emerald pickup, dam control-room button/bolt logic with low-tide reservoir crossings, the bell-book-candles exorcism path into Hades, glacier melting with the torch, mirror rubbing/breaking, the machine-room coal-to-diamond path, the safe/brick/fuse treasure path, generic container stashing (including the trophy case and mailbox), bulk `take/drop/put` handling for `all` and `valuables`, bat-room garlic behavior with live bat drops, gas-room open-flame deaths, shovel-driven digging at the beach and guano cave, a live thief encounter plus simplified roaming/stalking theft, the classic sharp-stick boat puncture gag plus putty repair for the damaged boat, sword glow warnings near villains, playable balloon travel in the volcano via the basket/receptacle/wire/hooks cluster, the carousel/low-room magnetic scramble with the CMACH round/square/triangular button cluster, and a live `score`/`quit` progress summary.

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
3. Extend the remaining late-game conditionals, object routines, fuller thief/scoring logic, balloon timing/collapse details, and deeper death handling.
4. Keep adding puzzle-specific behavior while preserving the data-driven room/object loader and condition/action registries.
5. Grow regression tests with every new mechanic so the port does not drift.
