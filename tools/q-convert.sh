#!/usr/bin/env bash
# PDF / Office / image  ->  PNG pages + text.txt in CLEAN/<name>/. The original is never opened on the host.
# shellcheck source=tools/_lib.sh
source "$(dirname "$0")/_lib.sh"
[ $# -eq 1 ] || die "usage: tools/q-convert.sh QUARANTINE/<file>"
f="$(in_quarantine "$1")"; [ -f "$f" ] || die "not a regular file"; need_image
out="$CLEAN/$(safe_name "$f")"; mkdir -p "$out"
docker run -i "${HARDEN[@]}" -v "$out:/out" "$IMAGE" convert < "$f" || { rmdir "$out" 2>/dev/null; exit 1; }
echo "result: $out"
