# Third-Party Notices

This file tracks bundled or runtime third-party components that should be
reviewed before the repository is made public.

## Bundled Data

- `meshdash/assets/offline_atlas_na.min.json` includes Natural Earth base layers
  and GeoNames city data. The file metadata identifies Natural Earth as Public
  Domain and GeoNames as CC BY 4.0.
- `meshdash/assets/chat_emoji_catalog.min.json` bundles an emoji catalog. Confirm
  and document the generation source before public release.
- `meshdash/games/zork/upstream_1977/zork-master/zork/dung.56` bundles upstream
  Zork data. Its redistribution status is not documented in this repository;
  confirm permission or remove it before public release.

## Runtime Network Assets

- The browser loads Leaflet and leaflet.heat from `unpkg.com` unless those assets
  are vendored or proxied.
- Online basemaps may load from OpenStreetMap or CARTO tile providers, depending
  on the selected map mode.
