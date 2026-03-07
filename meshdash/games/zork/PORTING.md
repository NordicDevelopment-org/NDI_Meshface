## Full Zork Port Notes

The current `zork/` bot app is a small Python example meant to be copied and adapted.
It is not yet a full port of the original game.

Reference source:

- `upstream_1977/zork-master/`

That source tree contains original 1977 MIT Zork files in MDL plus archival artifacts.
Meshyface cannot execute those files directly.

Practical porting strategy:

1. Treat the upstream MDL files as design/source reference.
2. Keep the runnable Meshyface implementation in `engine.py` and `world.py`.
3. Port the game incrementally:
   - room graph and descriptions
   - objects and inventory rules
   - parser verbs and aliases
   - puzzle/state transitions
   - scoring/win/death conditions
4. Keep the bot shell generic; keep game logic isolated in this folder.

This makes `zork/` both a working example bot app and the staging area for a future fuller Zork port.
