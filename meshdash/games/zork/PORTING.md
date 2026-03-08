## Full Zork Port Notes

The current `zork/` bot app is a small Python example meant to be copied and adapted.
It is not yet a full port of the original game.

## Current State

- Playable Meshyface game: still the small demo implementation in `engine.py` and `world.py`.
- Authoritative upstream reference source: `upstream_1977/zork-master/`
- Derived room extraction: `upstream_1977/extracted_rooms.json`
- Current extracted room count: `144`

The upstream source tree contains original 1977 MIT Zork files in MDL plus archival artifacts.
Meshyface cannot execute those files directly, so a full port means translation into the Python bot-app structure in this folder.

## What Is Already Ported

- The original source archive is vendored into the repo.
- A room extractor exists in `port_tools/extract_upstream_rooms.py`.
- `extracted_rooms.json` contains structured room data with:
  - `code`
  - `short_name`
  - `long_desc`
  - `exits`
  - `visible_object_codes`

## What Is Not Ported Yet

- The extracted classic room data is not wired into live gameplay yet.
- The original object model is not ported.
- The original parser behavior and verb set are not ported.
- Puzzle/state logic, scoring, death handling, and win conditions are not ported.
- The current playable game is still the simplified demo map.

## Regenerating Derived Data

If upstream source files change, regenerate the extracted room data with:

```bash
python -m meshdash.games.zork.port_tools.extract_upstream_rooms
```

That command rewrites `upstream_1977/extracted_rooms.json`.
Treat that file as generated data, not hand-edited source of truth.

## Porting Constraints

- Keep the transport/bot shell generic; game logic should stay in this folder.
- Keep the runnable Meshyface implementation in `engine.py` and `world.py`.
- Treat the upstream MDL files as design/source reference only.
- Meshyface is a short-text, turn-based chat environment, so some original output may need compression without changing game meaning.

## Recommended Port Order

1. Treat the upstream MDL files as design/source reference.
2. Replace the demo room graph with upstream room data.
3. Port objects and inventory rules.
4. Expand parser verbs and aliases.
5. Port puzzle/state transitions.
6. Add scoring, death, and win conditions.
7. Keep tests growing with the port so behavior does not drift.

## Definition Of Done

A reasonable "full enough" handoff target would be:

- The upstream room graph is navigable from the extracted data.
- Core object/inventory verbs work against the classic map.
- Major early-game puzzles behave like the upstream game.
- Replies remain mesh-friendly in size while preserving meaning.
- Regression tests cover room traversal, object interaction, and representative puzzle flows.

This makes `zork/` both a working example bot app and the staging area for a future fuller Zork port.
