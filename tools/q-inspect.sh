#!/usr/bin/env bash
# What is this file really, is it carrying anything active, and what to do next.
# The checks run in the container. The verdict line and the next step are written here, from a fixed
# set of words: the container says which case applies, but it never hands over a command to run.
# shellcheck source=tools/_lib.sh
source "$(dirname "$0")/_lib.sh"
[ $# -eq 1 ] || die "usage: tools/q-inspect.sh QUARANTINE/<file>"
f="$(in_quarantine "$1")"; [ -f "$f" ] || die "not a regular file"; need_image; no_shell_on "$f"
if { [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; } || [ -n "${FORCE_COLOR:-}" ]; then
  R=$'\033[1;31m'; G=$'\033[1;32m'; Y=$'\033[1;33m'; C=$'\033[36m'; B=$'\033[1m'; D=$'\033[2m'; N=$'\033[0m'
else R=; G=; Y=; C=; B=; D=; N=; fi
rel="${f#"$ROOT"/}"; name="$(basename -- "$f")"; P="$(quoted "$rel")"; DIR="$(quoted "$(dirname "$rel")")"

forged=0
show() {  # one line of the container's report, with the colours added here
  case "$1" in
    verdict:*|next:*|Q-RESULT*) forged=1; echo "  (a line was removed here)" ;;    # only this script writes those lines
    "  - "*)  printf '%s%s%s\n' "$Y" "$1" "$N" ;;
    "  "*)    printf '%s%s%s\n' "$D" "$1" "$N" ;;
    sha256:*) printf '%ssha256:%s%s%s%s\n' "$B" "$N" "$D" "${1#sha256:}" "$N" ;;
    file:*|type:*|mime:*|size:*|entries:*|links:*) printf '%s%s:%s%s\n' "$B" "${1%%:*}" "$N" "${1#*:}" ;;
    *) printf '%s\n' "$1" ;;
  esac
}

# Print the report, holding back its last line: that one must be "Q-RESULT <verdict> <kind>".
report() {
  local line last="" seen=0 verdict kind col msg nxt
  while IFS= read -r line || [ -n "$line" ]; do
    if [ "$seen" = 1 ]; then show "$last"; fi
    last="$line"; seen=1
  done
  if [[ ! "$last" =~ ^Q-RESULT\ (OK|CAUTION|STOP)\ ([a-z]+)$ ]]; then
    if [ "$seen" = 1 ]; then show "$last"; fi
    return $((1 + forged))
  fi
  # The real checks never print a verdict or a next step of their own. If the report has one, the
  # container is not running our checks any more, and its result is worth nothing.
  if [ "$forged" = 1 ]; then return 2; fi
  verdict="${BASH_REMATCH[1]}"; kind="${BASH_REMATCH[2]}"
  case "$verdict" in
    OK)      col=$G; msg="no known tricks found. Still, never open the original" ;;
    CAUTION) col=$Y; msg="suspicious content. Never open the original" ;;
    STOP)    col=$R; msg="dangerous file. Delete it and be wary of the sender" ;;
  esac
  printf '%sverdict:%s %s%s%s  %s\n' "$B" "$N" "$col" "$verdict" "$N" "$msg"
  if [ "$verdict" = STOP ]; then nxt="rm -- $P"
  else case "$kind" in
    pdf|office|image|text|markup) nxt="tools/q-convert.sh $P" ;;
    archive) nxt="tools/q-extract.sh $P" ;;
    code)    nxt="tools/q-shell.sh $DIR" ;;
    *)       nxt="ask the sender what this is; do not open it" ;;
  esac; fi
  printf '%snext:%s    %s%s%s\n' "$B" "$N" "$C" "$nxt" "$N"
}

set +e
docker run -i "${HARDEN[@]}" "$IMAGE" inspect "$name" < "$f" 2>&1 | plain | report
status=("${PIPESTATUS[@]}")
set -e
if [ "${status[2]}" = 2 ]; then
  die "the report held lines that only this script may write, so the checks cannot be trusted. Treat this file as hostile: delete it."
fi
if [ "${status[0]}" != 0 ] || [ "${status[2]}" != 0 ]; then
  failed "${status[0]}" "the inspection did not finish. Treat this file as dangerous: do not open it."
fi
