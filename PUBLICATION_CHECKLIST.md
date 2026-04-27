# Publication Checklist

Meshyface is currently staged as a private repository. Before making it public,
complete these checks.

## Required

- Choose and add the project license in `LICENSE`.
- Review bundled third-party data and code in `THIRD_PARTY_NOTICES.md`.
- Confirm the bundled Zork data may be redistributed publicly, or remove it.
- Confirm the bundled Unicode emoji catalog license or terms and record the
  generation command/input source.
- Review PyPI dependency license metadata and decide whether runtime/test
  versions should be pinned for the first public release.
- Confirm Leaflet, leaflet.heat, OpenStreetMap, and CARTO attribution/terms are
  acceptable for the documented runtime modes.
- Review AI-assisted changes for copied secrets, private data,
  attribution-sensitive snippets, and generated files that should not be
  shipped.
- Replace private hostnames, node IDs, screenshots, logs, and local paths in
  docs or examples.
- Run `python -m pytest -q`.

## Recommended

- Add release tags once the first public cut is ready.
- Decide whether GitHub Issues and Discussions should be enabled.
- Add screenshots only after checking they do not expose node IDs, locations,
  private channel names, PSKs, or LAN details.
