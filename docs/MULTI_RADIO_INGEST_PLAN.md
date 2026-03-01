# Multi-Radio Ingest Plan

## Problem

Support more than one radio (serial and/or remote TCP) feeding one dashboard and one history database, without inflating counts or duplicating chat/messages.

## Goals

1. Ingest from multiple radios in one running dashboard process.
2. Deduplicate packets across radios before they affect tracker state, chat feed, links, and history rollups.
3. Preserve source attribution so we can answer "which radio(s) heard this packet?"
4. Keep backward compatibility with current single-radio CLI and APIs.

## Non-Goals (Initial)

1. Distributed cluster consensus across multiple dashboard hosts.
2. Perfect dedupe for malformed packets missing sender/id fields.
3. Rewriting all history tables in one migration.

## Current State (Repo)

1. One interface is opened in `mesh_connection.py` and passed through runtime context.
2. Runtime subscribes a single tracker receive callback in `meshdash/dashboard_runtime_context.py`.
3. Packet/chat history writes are append-only:
   - packets: `meshdash/history_raw_writes.py`
   - chat: `meshdash/history_raw_writes.py`
   - packet events + rollups: `meshdash/history_writes.py`
4. There is no packet identity uniqueness constraint in current schema:
   - `meshdash/history_schema_tables.py`

## Architecture Overview

### Phase 1: Multi-Source Input (No Schema Breakage)

1. Add a new optional config input for sources:
   - `--mesh-sources-file /path/to/sources.json`
2. Keep existing `--mesh-port` and `--mesh-host` behavior:
   - if no sources file, runtime behaves exactly as today.
3. Introduce `open_mesh_interfaces(args)`:
   - returns a source registry and multiple interface objects.
   - each source has a stable `source_id`.
4. Runtime callback maps incoming `(packet, interface)` to `source_id`.

Example `sources.json`:

```json
{
  "sources": [
    { "id": "local-usb", "mode": "serial", "port": "/dev/ttyACM0" },
    { "id": "garage-tcp", "mode": "tcp", "host": "192.168.1.109", "port": 4403 }
  ]
}
```

### Phase 2: Runtime Dedupe Gate (Primary MVP)

1. Compute a canonical identity before tracker storage updates.
2. Suppress duplicates so duplicate packets do not:
   - increment live packet counters
   - duplicate chat entries
   - inflate link counts and rollups
3. Keep a bounded in-memory dedupe registry (LRU + TTL window).

Proposed identity strategy:

1. Primary key when available: `from_id + packet_id`.
2. Duplicate decision: same primary key within a short time window (for example 120-300s) is duplicate.
3. Fallback key when packet id is missing: hash of stable fields (`from`, `to`, `portnum`, decoded text/payload signature, channel, hop_start, hop_limit).

Reasoning:

1. `from + packet_id` is source-independent and catches same mesh packet heard by multiple radios.
2. Time window avoids false duplicate suppression from very old packet-id reuse.

### Phase 3: Source Attribution Persistence

Add additive tables (no destructive migration):

1. `ingest_sources`
   - `source_id` primary key
   - source mode/endpoint metadata
   - last seen timestamps and status
2. `packet_sightings`
   - one row per source observation
   - includes canonical packet identity key + source id + per-source RSSI/SNR/hops
   - indexed by packet identity and source id

Canonical packet/history rows remain one-per-message. Sightings preserve "heard by N radios" detail.

### Phase 4: Optional Remote Push Mode

If central host cannot directly reach all radios, add optional ingest endpoint:

1. `POST /api/ingest/packet` (token-authenticated)
2. payload includes packet + `source_id`
3. central runtime runs same dedupe gate and storage path

This allows remote edge collectors to push into one central DB.

## Data Model Changes (Additive)

### New Tables

1. `ingest_sources`
2. `packet_sightings`

### Optional Additive Columns (if needed for quick joins)

1. `packets.first_source_id`
2. `chat.first_source_id`
3. `packet_events.first_source_id`

These should be additive only, nullable, and backfilled lazily if needed.

## Duplicate Handling Details

1. Dedupe happens before `apply_tracker_storage_updates(...)` in `meshdash/tracker_storage.py` path.
2. Canonical packet flow:
   - normal tracker update
   - normal packet/chat/history writes
   - optional sighting write
3. Duplicate packet flow:
   - skip canonical tracker/history writes
   - write sighting only (optional by phase)

Collision/risk handling:

1. Packet-id reuse by a node over long periods is handled by time-windowed dedupe decisions.
2. Missing packet id uses a weaker fallback key and can still produce occasional duplicates.
3. Keep dedupe window configurable for tuning.

## Implementation Plan

1. Add source config parser and validation.
2. Add multi-interface open/close manager.
3. Thread `source_id` through receive pipeline and packet summary builders.
4. Add runtime dedupe registry and gate before storage updates.
5. Add tests for dedupe correctness and counter integrity.
6. Add `ingest_sources` and `packet_sightings` tables plus writes.
7. Add API payload fields for source status and optional sighting counts.
8. Add optional remote push ingest endpoint later.

## Testing Matrix

1. Unit tests:
   - key generation (primary/fallback)
   - dedupe window behavior
   - source id routing from interface to packet handling
2. Runtime behavior tests:
   - two sources emit same packet, only one canonical chat/packet entry appears
   - live counters and link metrics increment once
3. Persistence tests:
   - canonical packet stored once
   - sightings stored per source
4. Regression tests:
   - single-source mode unchanged
   - existing API/state payload still valid when source metadata absent

## Rollout and Rollback

1. Ship behind feature flag/config:
   - default single-source behavior
   - multi-source enabled only when `--mesh-sources-file` is provided
2. Start with Phase 1+2 in staging.
3. Verify:
   - no duplicate chat rows
   - stable packet/link counters
   - expected CPU/memory with dedupe cache
4. Enable source attribution tables and optional UI fields.
5. Rollback path:
   - disable multi-source config/flag
   - keep additive schema; old runtime ignores new tables.

## Effort Estimate

1. Phase 1+2 MVP: medium, about 2-4 focused development sessions.
2. Phase 3 source attribution persistence: medium, about 1-3 additional sessions.
3. Phase 4 remote push ingest mode: medium-high, about 2-4 sessions including auth/hardening.

## Open Questions

1. Should dedupe window be global or per-source/per-port?
2. Do we want to show "heard by X radios" in UI immediately or later?
3. Is remote push mode required now, or is direct TCP reachability enough for first delivery?
4. Should we persist dedupe registry to DB for restart continuity, or keep runtime-only in MVP?
