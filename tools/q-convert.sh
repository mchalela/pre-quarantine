#!/usr/bin/env bash
# PDF / Office / image  ->  PNG pages + text.txt in CLEAN/<sender>/<name>/. The original is never opened on the host.
# shellcheck source=tools/_lib.sh
source "$(dirname "$0")/_lib.sh"
[ $# -eq 1 ] || die "usage: tools/q-convert.sh QUARANTINE/<file>"
f="$(in_quarantine "$1")"; [ -f "$f" ] || die "not a regular file"; need_image
# Keep the sender's subfolder, and only that level: QUARANTINE/<sender>/.../<file> -> CLEAN/<sender>/<file>/.
# Deeper folders come from extracted archives, so their names are the sender's choice.
dest="$CLEAN"; rel="${f#"$Q"/}"
case "$rel" in */*) dest="$CLEAN/$(safe_name "${rel%%/*}")" ;; esac
out="$dest/$(safe_name "$f")"; mkdir -p "$out"
if ! docker run -i "${HARDEN[@]}" -v "$out:/out" "$IMAGE" convert < "$f"; then
  rmdir "$out" 2>/dev/null || true
  if [ "$dest" != "$CLEAN" ]; then rmdir "$dest" 2>/dev/null || true; fi
  exit 1
fi
echo "result: $out"
