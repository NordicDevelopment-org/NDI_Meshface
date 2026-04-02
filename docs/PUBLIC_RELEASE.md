# Public Release Workflow

Doc status: active-runtime
Last reviewed: 2026-04-02

This repo stays private for development while publishing curated snapshots to a
separate public repo.

## Long-term branch model

Source of truth:

- `main` in private repo (`mesh_py`)

Public staging branch in private repo:

- `release/public-v0`

Public publish target:

- remote `meshyface` (public repo)
- branch `release-candidate` (then PR/merge to public `main`)

Day-to-day flow:

1. Branch from `main` for feature work.
2. Merge feature work back into `main`.
3. Sync `release/public-v0` from `main` when you are ready to cut a public
   candidate.
4. Publish only allowlisted files via `scripts/release_public.sh`.

## Default release config

Config file:

- `.public-release/config.env`

Defaults:

```bash
PUBLIC_RELEASE_REMOTE=meshyface
PUBLIC_RELEASE_BRANCH=release-candidate
PUBLIC_RELEASE_PROFILE=core-ui
```

Runtime UI profile for deployed dashboards is independent from file allowlists.
Use `MESH_DASH_UI_PROFILE=core-ui` on public hosts to trim game/file/bot-heavy
frontend modules while keeping private `main` at `full`.

## Curate what can go public

Profile allowlists live in:

- `.public-release/allowlists/*.allowlist`

Current profiles:

- `core-ui`: chat + network + console + settings release rail
- `sdk`: SDK/docs-only export

List profiles:

```bash
./scripts/release_public.sh --list-profiles
```

Allowlist rules:

- one repo-root-relative path per line
- blank lines and `# comments` are ignored
- keep list explicit and minimal

Regenerate the `core-ui` allowlist after runtime/import refactors:

```bash
./scripts/generate_core_ui_allowlist.py --validate
```

## Sync + publish flow

Sync staging branch from `main`:

```bash
git checkout release/public-v0
git merge main
git push origin release/public-v0
git checkout main
```

Preflight public drift guard (recommended before publish):

```bash
./scripts/check_public_branch_drift.sh \
  --base-branch main \
  --public-branch release/public-v0 \
  --allowlist .public-release/allowlists/public-v0-drift.allowlist
```

`scripts/release_public.sh` now runs this guard automatically when source branch
is `release/public-v0`. It will fail if public-only drift spreads beyond the
approved file list.

Dry-run publish:

```bash
./scripts/release_public.sh --source-branch release/public-v0 --dry-run
```

Bypass drift guard only for emergencies:

```bash
./scripts/release_public.sh --source-branch release/public-v0 --skip-drift-check --dry-run
```

Publish:

```bash
./scripts/release_public.sh --source-branch release/public-v0
```

Optional overrides:

```bash
./scripts/release_public.sh \
  --source-branch release/public-v0 \
  --profile sdk \
  --target-branch release-sdk \
  --message "Public v0.1 snapshot"
```

After publish to `release-candidate`, open a PR in `meshyface`:

- base: `main`
- compare: `release-candidate`

## Safety notes

- The script refuses to run if the source repo has uncommitted changes
  (unless `--allow-dirty` is set).
- On first publish to a new public branch, it creates an orphan release branch
  so private commit history is not pushed.
- It prints the exact file list queued for release before pushing.
