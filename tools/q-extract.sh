#!/usr/bin/env bash
# Unpack an archive inside the container. Output stays in QUARANTINE/<name>.extracted/ (still untrusted).
#   tools/q-extract.sh QUARANTINE/<archive> [--big]     --big: accept more than 2 GB or 100000 entries
# shellcheck source=tools/_lib.sh
source "$(dirname "$0")/_lib.sh"
big=0
if [ $# -eq 2 ] && [ "$2" = --big ]; then big=1; set -- "$1"; fi
[ $# -eq 1 ] || die "usage: tools/q-extract.sh QUARANTINE/<archive> [--big]"
f="$(in_quarantine "$1")"; [ -f "$f" ] || die "not a regular file"; need_image; no_shell_on "$f"
out="$(dirname "$f")/$(safe_name "$f").extracted"
if [ -e "$out" ] || [ -L "$out" ]; then die "already exists: $out"; fi

stage=""
trap 'discard "$stage"' EXIT
stage="$(scratch)"
rc=0
docker run -i "${HARDEN[@]}" -e Q_BIG="$big" -v "$stage:/out" "$IMAGE" extract < "$f" 2>&1 | plain || rc=$?
# The container is not trusted to clean up after itself, so that happens here, whatever went on in there.
tidy "$stage"
count="$(find "$stage" -type f | wc -l)"
if [ "$rc" != 0 ] && [ "$count" = 0 ]; then failed "$rc" "nothing was extracted."; fi
mv -T -- "$stage" "$out"

echo "$count file(s) extracted (links and special files removed, exec bits cleared)"
if [ -n "$(find "$out" -name .git -print -quit)" ]; then
  echo "note: there is a git repository inside. Never run git in that folder on the host: its config can run commands."
fi
echo "result: $(quoted "$out")   (still quarantined: treat each file by its own type)"
[ "$rc" = 0 ] || failed "$rc" "the archive did not unpack cleanly. What could be read is in the folder above; some of it may be missing."
