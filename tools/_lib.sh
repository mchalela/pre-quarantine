# shellcheck shell=bash
# Shared by the q-*.sh scripts. Not meant to be run directly.
# shellcheck disable=SC2034  # the variables below are used by the scripts that source this file
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
Q="$ROOT/QUARANTINE"; CLEAN="$ROOT/CLEAN"; IMAGE="${Q_IMAGE:-quarantine-tools}"   # Q_IMAGE: used by the tests

die() { echo "error: $*" >&2; exit 1; }

# Resolve $1 and insist it lives under QUARANTINE/.
in_quarantine() {
  local p; p="$(realpath -e -- "$1" 2>/dev/null)" || die "no such path: $1"
  case "$p" in "$Q"/*) printf '%s' "$p" ;; *) die "refusing: $p is not inside $Q" ;; esac
}
safe_name() { printf '%s' "$(basename -- "$1")" | tr -c 'A-Za-z0-9._-' '_' | cut -c1-80; }
need_image() { docker image inspect "$IMAGE" >/dev/null 2>&1 || die "image missing. Run: tools/build.sh"; }

# Locked-down container: no network, no capabilities, read-only root, nothing of the host but /out.
# shellcheck disable=SC2054  # the commas belong to the tmpfs option
HARDEN=(--rm --network none --cap-drop ALL --security-opt no-new-privileges
        --read-only --tmpfs /tmp:rw,size=2g,mode=1777 --user "$(id -u):$(id -g)"
        --memory 4g --pids-limit 512)
