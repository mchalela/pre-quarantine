#!/usr/bin/env bash
# Unpack an archive inside the container. Output stays in QUARANTINE/<name>.extracted/ (still untrusted).
# shellcheck source=tools/_lib.sh
source "$(dirname "$0")/_lib.sh"
[ $# -eq 1 ] || die "usage: tools/q-extract.sh QUARANTINE/<archive>"
f="$(in_quarantine "$1")"; [ -f "$f" ] || die "not a regular file"; need_image
out="$(dirname "$f")/$(safe_name "$f").extracted"; [ -e "$out" ] && die "already exists: $out"; mkdir -p "$out"
docker run -i "${HARDEN[@]}" -v "$out:/out" "$IMAGE" extract < "$f"
echo "result: $out   (still quarantined: treat each file by its own type)"
