#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Validate that public branch divergence from base branch only touches approved files.

Usage:
  ./scripts/check_public_branch_drift.sh [options]

Options:
  --base-branch <name>     Base/private branch (default: $PUBLIC_DRIFT_BASE_BRANCH or main)
  --public-branch <name>   Public staging branch (default: $PUBLIC_DRIFT_BRANCH or release/public-v0)
  --allowlist <path>       Drift allowlist path (default: $PUBLIC_DRIFT_ALLOWLIST or .public-release/allowlists/public-v0-drift.allowlist)
  -h, --help               Show this help

Allowlist format:
  - One repo-root-relative pattern per line.
  - Blank lines and lines starting with # are ignored.
  - Exact paths are supported.
  - Globs are supported (for example: meshdash/assets/*.tmpl).
  - Directory prefixes are supported with trailing slash (for example: docs/public/).
EOF
}

die() {
  echo "error: $*" >&2
  exit 1
}

require_arg() {
  local arg_name="$1"
  local arg_value="${2-}"
  [[ -n "$arg_value" ]] || die "missing value for ${arg_name}"
}

trim() {
  local value="$1"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  printf '%s' "$value"
}

base_branch="${PUBLIC_DRIFT_BASE_BRANCH:-main}"
public_branch="${PUBLIC_DRIFT_BRANCH:-release/public-v0}"
allowlist_file="${PUBLIC_DRIFT_ALLOWLIST:-.public-release/allowlists/public-v0-drift.allowlist}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-branch)
      require_arg "$1" "${2-}"
      base_branch="$2"
      shift 2
      ;;
    --public-branch)
      require_arg "$1" "${2-}"
      public_branch="$2"
      shift 2
      ;;
    --allowlist)
      require_arg "$1" "${2-}"
      allowlist_file="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unknown argument: $1"
      ;;
  esac
done

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

git rev-parse --verify "${base_branch}^{commit}" >/dev/null 2>&1 || die "invalid base branch/commit: ${base_branch}"
git rev-parse --verify "${public_branch}^{commit}" >/dev/null 2>&1 || die "invalid public branch/commit: ${public_branch}"
[[ -f "$allowlist_file" ]] || die "drift allowlist file not found: ${allowlist_file}"

allow_patterns=()
while IFS= read -r raw_line || [[ -n "$raw_line" ]]; do
  line="$(trim "$raw_line")"
  [[ -z "$line" ]] && continue
  [[ "${line:0:1}" == "#" ]] && continue
  if [[ "$line" == /* ]]; then
    die "allowlist entry must be repo-relative, not absolute: $line"
  fi
  if [[ "$line" == ".." || "$line" == ../* || "$line" == */.. || "$line" == */../* ]]; then
    die "allowlist entry cannot escape repository root: $line"
  fi
  if [[ "$line" == */ ]]; then
    allow_patterns+=("${line}*")
  else
    allow_patterns+=("$line")
  fi
done < "$allowlist_file"

[[ "${#allow_patterns[@]}" -gt 0 ]] || die "drift allowlist is empty: ${allowlist_file}"

mapfile -t changed_paths < <(git diff --name-only "${base_branch}..${public_branch}" | sed '/^[[:space:]]*$/d')

if [[ "${#changed_paths[@]}" -eq 0 ]]; then
  echo "drift-check: ${public_branch} matches ${base_branch} (no divergent files)."
  exit 0
fi

violations=()
for path in "${changed_paths[@]}"; do
  matched=0
  for pattern in "${allow_patterns[@]}"; do
    if [[ "$path" == $pattern ]]; then
      matched=1
      break
    fi
  done
  if [[ "$matched" -eq 0 ]]; then
    violations+=("$path")
  fi
done

if [[ "${#violations[@]}" -gt 0 ]]; then
  echo "drift-check: FAILED" >&2
  echo "  base branch  : ${base_branch}" >&2
  echo "  public branch: ${public_branch}" >&2
  echo "  allowlist    : ${allowlist_file}" >&2
  echo >&2
  echo "Unapproved divergent files:" >&2
  printf '  - %s\n' "${violations[@]}" >&2
  echo >&2
  echo "All divergent files (${#changed_paths[@]} total):" >&2
  printf '  - %s\n' "${changed_paths[@]}" >&2
  echo >&2
  echo "Add intentional public-only files to ${allowlist_file} before releasing." >&2
  exit 1
fi

echo "drift-check: OK (${public_branch} diverges from ${base_branch} only in approved files)."
printf '  - %s\n' "${changed_paths[@]}"
