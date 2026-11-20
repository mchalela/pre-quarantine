# shellcheck shell=bash
# Shared by the q-*.sh scripts. Not meant to be run directly.
# shellcheck disable=SC2034  # the variables below are used by the scripts that source this file
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
Q="$ROOT/QUARANTINE"; CLEAN="$ROOT/CLEAN"; IMAGE="${Q_IMAGE:-quarantine-tools}"   # Q_IMAGE: used by the tests

# The container is where hostile files get parsed, so the host trusts nothing it says or writes.
# Whatever it prints, and any file name, reaches the terminal as printable ASCII, never as control codes.
plain()  { LC_ALL=C tr -c '\n\040-\176' '?'; }
quoted() { (LC_ALL=C; printf '%q' "$1"); }      # a path as one shell word, in plain ASCII
die() { printf 'error: %s\n' "$*" | plain >&2; exit 1; }

# A working install runs the helper-agent rules as copies of agent/*. Say so when they fall behind
# (for example after a git pull). Development clones have no marker and are left alone.
if [ -e "$ROOT/.claude/.agent-rules-installed" ]; then
  if ! cmp -s "$ROOT/agent/CLAUDE.md" "$ROOT/CLAUDE.md" ||
     ! cmp -s "$ROOT/agent/settings.json" "$ROOT/.claude/settings.json"; then
    echo "warning: the helper-agent rules here are missing or out of date. Run: tools/install-agent-rules.sh" >&2
  fi
fi

# Resolve $1 and insist it lives under QUARANTINE/.
in_quarantine() {
  local p; p="$(realpath -e -- "$1" 2>/dev/null)" || die "no such path: $1"
  case "$p" in "$Q"/*) printf '%s' "$p" ;; *) die "refusing: $p is not inside $Q" ;; esac
}
# A folder name for CLEAN/: plain characters only, and never hidden or shaped like a command option.
safe_name() {
  local n; n="$(printf '%s' "$(basename -- "$1")" | LC_ALL=C tr -c 'A-Za-z0-9._-' '_' | cut -c1-80)"
  case "$n" in [.-]*) n="_${n#?}" ;; esac
  printf '%s' "$n"
}
# The image has to be there, and built from this version of the tools: the scripts and the image
# agree on what the container prints (see the label in tools/image/Dockerfile).
need_image() {
  local v; v="$(docker image inspect -f '{{index .Config.Labels "pre-quarantine.protocol"}}' "$IMAGE" 2>/dev/null)" ||
    die "image missing. Run: tools/build.sh"
  [ "$v" = 2 ] || die "the tools image was not built from this version of the scripts. Run: tools/build.sh"
}

# Code running in a sandbox shell can change its folder at any moment, for example swap a file for
# a link between the check above and the moment a tool opens it. So the tools stay out of a folder
# while a shell is open on it. q-shell.sh labels its container with the folder to make this possible.
no_shell_on() {
  local d
  while IFS= read -r d; do
    [ -n "$d" ] || continue
    case "$1" in "$d"/*) die "a sandbox shell is open on $d. Close it first." ;; esac
  done < <(docker ps --filter label=pre-quarantine.shell --format '{{.Label "pre-quarantine.shell"}}' 2>/dev/null)
}

# Locked-down container: no network, no capabilities, read-only root, nothing of the host but /out.
# shellcheck disable=SC2054  # the commas belong to the tmpfs option
HARDEN=(--rm --network none --cap-drop ALL --security-opt no-new-privileges
        --read-only --tmpfs /tmp:rw,size=2g,mode=1777 --user "$(id -u):$(id -g)"
        --memory 4g --memory-swap 4g --pids-limit 512)

# Say why a container run ended badly. Status 137 means it was killed: by the time limit built into
# the image, or by the kernel for using more memory than it is allowed.
failed() {  # $1 = exit status   $2 = what to say otherwise
  if [ "$1" = 137 ]; then die "stopped: it ran past the time limit or the memory limit. Treat the file as hostile."; fi
  die "$2"
}

# The container writes into a scratch folder under QUARANTINE/, never straight into its final place:
# what it leaves behind is checked or tidied on the host first, and thrown away if anything goes wrong.
scratch() { mktemp -d "$Q/.q-XXXXXX"; }
discard() {
  local d
  for d in "$@"; do
    case "$d" in "$Q"/.q-??????) ;; *) continue ;; esac
    [ -d "$d" ] || continue
    chmod -R u+rwX -- "$d" 2>/dev/null || true
    rm -rf -- "$d"
  done
}

# Make a folder the container wrote safe to keep: every folder reachable, nothing but plain files
# and folders (no links, pipes or devices), nothing executable.
tidy() {
  ( cd -- "$1"
    chmod -R u+rwX -- .
    find . -mindepth 1 ! -type f ! -type d -delete
    find . -type d -exec chmod 0755 {} +
    find . -type f -exec chmod 0644 {} + )
}

# Text on its way to CLEAN/: no control characters (so no escape codes, in either of their two
# spellings), but tabs, newlines and accented letters stay.
text_only() { LC_ALL=C tr -d '\000-\010\013-\037\177' | LC_ALL=C sed $'s/\xc2[\x80-\x9f]//g'; }
