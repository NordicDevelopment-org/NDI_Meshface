## Full Zork Port Notes

The current `zork/` bot app is a small Python example meant to be copied and adapted.
It is not yet a full port of the original game.

## Current State

- Playable Meshyface game: classic opening now live in `engine.py` + `world.py`, powered by the upstream room graph and parsed object data.
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

## What Is Already Live

- A classic-room live map is wired into gameplay.
- Upstream object data is parsed into the live game, including visible items, containers, aliases, and readable text.
- The live parser now supports movement, inventory, take/drop, look/examine/read, targeted light/extinguish actions, open/close/unlock, put/insert, throw/rub, move/lift, dig, wave, tie/untie, push/press, turn, inflate/deflate, prayer/exorcism actions, magic-word actions, and early combat.
- The house/mailbox/window/trap-door/grating/troll path is playable in the live game.
- Rope-and-dome traversal, the riddle-room word, cyclops bypass, rainbow toggling, and real board/launch/land/disembark inflatable-boat travel are wired into the live game.
- Dam control-room button/bolt behavior, low-tide reservoir crossings, and the bell-book-candles exorcism route into Hades are now wired into the live game.
- The glacier can now be melted the classic way with the torch, mirror rubbing/breaking now behaves like the original trick, the machine room can now transmute coal into a diamond (or junk into slag), and the safe/brick/fuse path now opens the safe and reveals its treasures.
- The red buoy can now be opened in the river, revealing the emerald inside, and the river/falls path can now actually kill you instead of acting like decorative plumbing.
- Generic container insertion now works for normal open containers, the living-room trophy case is now a real stash point instead of scenery, and bulk `take/drop/put` handling for `all` and `valuables` is wired in.
- `score` and `quit` now report live progress from seen room bonuses plus treasure recovery/security, so the port has a reusable progress layer instead of just hard-ending sessions.
- The engine now has a reusable room-entry hazard path for special rooms, so the bat room can fling you into the mines, the gas room can punish open flames, and late-game room-specific handlers have a cleaner place to live.
- The beach and guano cave now have shovel-driven digging behavior, the treasure room can now spring the thief hideout encounter, and the sword now warns about nearby villains with the classic blue-glow behavior.
- The thief can now stalk treasure carriers through the deeper dungeon, steal carried/loose treasure on room entry, and flee with it instead of remaining a treasure-room-only mannequin.
- Boarding the inflated boat while carrying the broken sharp stick now punctures it into the damaged boat, and the damaged boat can be repaired back into the inflatable boat with putty.
- The volcano balloon cluster is now playable: the basket/receptacle/wire/hooks are live, burnable fuel in the receptacle inflates the balloon, wire-to-hook tie/untie works on the ledges, and board/launch/land/disembark balloon travel plus rim/bad-landing failures are wired into the live game.
- The carousel/low-room magnetic cluster is now playable: the round room can now either randomize or honor directional exits, the low room now routes to the machine room or Alice depending on the magnetic state, and the CMACH round/square/triangular buttons now control the flip/zoom behavior instead of leaving that branch as a dead end.
- The robot/sphere/high-voltage cluster is now partly canonical: pressing the CMACH buttons by hand now fries the player, actor-style `robot ...`/`tell robot ...` commands can move the robot and make it press the buttons safely, the crystal-sphere cage trap now works, and the robot can now raise the cage or ruin the sphere by trying to grab it himself.

## What Is Still Missing

- Late-game condition flags, richer object routines, canonical scoring details, deeper death/restart handling, and the full puzzle set are still incomplete.
- River/boat travel now supports the main board/launch/land/disembark flow, but the boat is not yet a fully canonical vehicle container and the wider river puzzle web is still incomplete.
- Balloon travel is now playable, but it is still simplified compared with the upstream clock-driven automatic ascent/descent logic and broader volcano timing details.
- The safe path is now playable, but its fuse timing is intentionally simplified compared with full upstream timing.
- Glacier, mirror, thief, machine, safe, carousel, and other later puzzle clusters still need fuller canonical behavior.
- The thief now roams and steals in a deterministic simplified way, but he is still not the full upstream robber demon with canonical randomness, hiding rules, or complete combat behavior.
- The carousel/CMACH branch is now traversable, and the high-voltage/robot mediation is now live at a basic actor-command level, but broader robot behavior is still simplified compared with the original actor system.
- The sphere/cage gas clock is now playable, but its timing and actor behavior are still simplified compared with the upstream event clock.

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
5. Port puzzle/state transitions, preferably through reusable condition/action registries instead of one-off branches.
6. Add scoring, death, and win conditions.
7. Keep tests growing with the port so behavior does not drift.

## Definition Of Done

A reasonable "full enough" handoff target would be:

- [done] The upstream room graph is navigable from the live game.
- [done] Core object/inventory verbs work against the classic map.
- [partial] Major early-game puzzles behave like the upstream game.
- [done] Replies remain mesh-friendly in size while preserving meaning.
- [partial] Regression tests cover room traversal, object interaction, and representative puzzle flows.

This makes `zork/` both a working example bot app and the staging area for a future fuller Zork port.
