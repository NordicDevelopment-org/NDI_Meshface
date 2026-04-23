# Publication Checklist

Meshyface is currently staged as a private repository. Before making it public,
complete these checks.

## Required

- Choose and add the project license in `LICENSE`.
- Review bundled third-party data and code in `THIRD_PARTY_NOTICES.md`.
- Confirm the bundled Zork data may be redistributed publicly, or remove it.
- Confirm the bundled emoji catalog source and license, or regenerate it from a
  clearly attributed source.
- Replace private hostnames, node IDs, screenshots, logs, and local paths in
  docs or examples.
- Run `python -m pytest -q`.

## Recommended

- Add release tags once the first public cut is ready.
- Decide whether GitHub Issues and Discussions should be enabled.
- Add screenshots only after checking they do not expose node IDs, locations,
  private channel names, PSKs, or LAN details.
