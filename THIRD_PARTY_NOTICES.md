# Third-Party Notices

This file tracks bundled or runtime third-party components that should be
reviewed before the repository is made public.

## Bundled Data

- `meshdash/assets/dashboard.js.chat.events.core.identity.favorites_selection.favorites_state_ui.tmpl`
  embeds the `mdiNewBox` SVG path from Material Design Icons / `@mdi/js`
  for the automatic "New" node tag icon. Material Design Icons are distributed
  under Apache License 2.0.
- `meshdash/assets/offline_atlas_na.min.json` includes Natural Earth global
  110m base layers, Natural Earth/North America detail layers, and GeoNames
  city data. The file metadata identifies Natural Earth as Public Domain and
  GeoNames as CC BY 4.0.
- `meshdash/assets/chat_emoji_catalog.min.json` bundles an emoji catalog
  generated from Unicode `emoji-test.txt`. The current payload identifies
  Unicode Emoji version `17.0`, dated `2025-08-04, 20:55:31 GMT`. Before public
  release, document the exact generation command/input URL and confirm the
  applicable Unicode data license or terms.
- `meshdash/games/zork/upstream_1977/zork-master/zork/dung.56` bundles Zork
  data sourced from `https://github.com/MITDDC/zork`, the MIT Libraries
  Department of Distinctive Collections repository for a 1977 version of Zork.
  The source repository includes rights and license details; review them before
  public release.
- `meshdash/games/adventure/data/77-03-31_adventure.dat` bundles Colossal Cave
  Adventure data copied from `https://github.com/wh0am1-dev/adventure`. The
  source repository describes the material as original Fortran source collected
  for educational purposes, but does not document redistribution terms; confirm
  permission or remove it before public release.

## Runtime Network Assets

- The browser loads Leaflet `1.9.4` and leaflet.heat `0.2.0` from `unpkg.com`
  unless those assets are vendored or proxied.
- Online basemaps may load from OpenStreetMap or CARTO tile providers, depending
  on the selected map mode. Review provider attribution and tile-use terms before
  public release or hosted deployment.

## Python Dependencies

- Runtime dependencies are installed from PyPI via `requirements.txt`:
  `meshtastic`, `pypubsub`, and `protobuf`.
- Test dependencies are installed from PyPI via `requirements-dev.txt`, which
  currently adds `pytest`.
- Before public release, review package license metadata and pin versions for
  reproducible release builds if needed.

## AI-Assisted Contributions

Some source code, documentation, and tests in this repository may have been
created or edited with AI-assisted development tools. Maintainers review,
modify, and accept project responsibility for committed changes.

AI assistance is not treated as a bundled third-party runtime component. Known
bundled data, external assets, and package dependencies are tracked separately
above.
