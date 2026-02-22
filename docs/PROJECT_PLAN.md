# Mesh Dashboard Product Plan

## North Star

Build a **Teams-like chat experience for Meshtastic networks** with integrated network awareness in one window:

- Chat is primary.
- Network/map/history cards are contextual.
- Operators can move from conversation -> node diagnostics -> link quality without changing tools.

## Product Direction

1. Chat-first UX
2. Live + historical telemetry side-by-side
3. Persistent state for replay and benchmarking
4. LAN-hosted, low-friction deployment

## Milestones

### Phase 1: Stability Foundation (current)

- Reliable dashboard service + history DB
- Per-message emoji reactions with protocol compatibility
- Node selection syncing across chat/map/list
- Initial tests for core parsing and transport helpers

### Phase 2: Unified Workspace

- Promote chat pane to primary surface
- Context panel updates from selected message/node
- Reduce duplicated cards and merge related panels
- Add better layout presets for desktop vs mobile

### Phase 3: Mesh Intelligence

- Historical trends by node/link (SNR, RSSI, hops)
- Connection reliability scoring over time
- Saved views for antenna/site benchmarking
- Exportable snapshots for analysis

## Non-Goals (for now)

- Full enterprise identity/auth stack
- Cloud multi-tenant backend
- Replacing the official Meshtastic app

## Engineering Plan

1. Keep runtime simple (`mesh_dashboard.py` entrypoint remains)
2. Improve testability with pure helper functions + pytest
3. Incrementally split large modules only after test coverage is in place
4. Keep all deprecated tools in `archive/` with clear labels
5. Execute staged modularization in `docs/REFACTOR_ROADMAP.md`

## Definition of Done For New Features

- Works live with existing service deployment flow
- Persists correctly in history (if feature touches chat/traffic)
- Has pytest coverage for parsing/state behavior
- README/docs updated when behavior changes
