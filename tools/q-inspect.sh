#!/usr/bin/env bash
# What is this file really, is it carrying anything active, and what to do next.
# shellcheck source=tools/_lib.sh
source "$(dirname "$0")/_lib.sh"
[ $# -eq 1 ] || die "usage: tools/q-inspect.sh QUARANTINE/<file>"
f="$(in_quarantine "$1")"; [ -f "$f" ] || die "not a regular file"; need_image
color=0; [ -t 1 ] && [ -z "${NO_COLOR:-}" ] && color=1; [ -n "${FORCE_COLOR:-}" ] && color=1
rel="${f#"$ROOT"/}"; name="$(basename -- "$f")"
docker run -i "${HARDEN[@]}" -e Q_COLOR="$color" \
  -e Q_PATH="$(printf '%q' "$rel")" -e Q_DIR="$(printf '%q' "$(dirname "$rel")")" \
  "$IMAGE" inspect "$name" < "$f"
