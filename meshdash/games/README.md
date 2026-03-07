Mini-games for `MeshResponseBot` live here.

The current bot app example lives in `meshdash/games/zork/`.
That folder now also includes `upstream_1977/zork-master/`, which is the archived MIT Zork source used as the reference for a future fuller port.

If you want to make your own game:

1. Copy the `zork/` folder.
2. Rename the class/command metadata in your copied `engine.py`.
3. Change the room map and rules there.
4. Register your copied app in `meshdash/bot_apps/registry.py`.

The goal is to keep the app code separate from the transport, logging, and bot settings code.
