#!/usr/bin/env bash
# PDF / Office / image  ->  PNG pages + text.txt in CLEAN/<sender>/<name>/. The original is never opened on the host.
# shellcheck source=tools/_lib.sh
source "$(dirname "$0")/_lib.sh"
[ $# -eq 1 ] || die "usage: tools/q-convert.sh QUARANTINE/<file>"
f="$(in_quarantine "$1")"; [ -f "$f" ] || die "not a regular file"; need_image; no_shell_on "$f"
# Keep the sender's subfolder, and only that level: QUARANTINE/<sender>/.../<file> -> CLEAN/<sender>/<file>/.
# Deeper folders come from extracted archives, so their names are the sender's choice.
dest="$CLEAN"; rel="${f#"$Q"/}"
case "$rel" in */*) dest="$CLEAN/$(safe_name "${rel%%/*}")" ;; esac
out="$dest/$(safe_name "$f")"
# Two originals can map to the same folder (one name in two subfolders, or names that differ only in
# odd characters), and an old conversion may hold more pages than a new one. Never mix: refuse.
if [ -e "$out" ] || [ -L "$out" ]; then die "already there: $out. Delete that folder to convert again."; fi

stage=""; checked=""
trap 'discard "$stage" "$checked"' EXIT
stage="$(scratch)"; checked="$(scratch)"
rc=0
docker run -i "${HARDEN[@]}" -v "$stage:/out" "$IMAGE" convert < "$f" 2>&1 | plain || rc=$?
[ "$rc" = 0 ] || failed "$rc" "conversion failed. Nothing was written to CLEAN/."

# Only what the converter is meant to produce gets through: plain files called page-NNN.png that
# start like a PNG, and the two text files. Anything else means the converter was taken over.
odd() { die "the converter left something it should not have ($1). Nothing was kept: treat the original as hostile."; }
# Sizes as the files claim them, holes included: the copies made below would turn a hole into real data.
[ "$(du -sb -- "$stage" | cut -f1)" -le 4294967296 ] || odd "more than 4 GB of output"
shopt -s nullglob dotglob
count=0
for p in "$stage"/*; do
  n="${p##*/}"
  if [ -L "$p" ] || [ ! -f "$p" ]; then odd "$n"; fi
  if [[ "$n" =~ ^page-[0-9]{3,4}\.png$ ]]; then
    head -c 8 -- "$p" | cmp -s - <(printf '\211PNG\r\n\032\n') || odd "$n"
    cat -- "$p" > "$checked/$n"            # a fresh copy: no permission bits or attributes come along
  elif [ "$n" = text.txt ] || [ "$n" = content.txt ]; then
    text_only < "$p" > "$checked/$n"
  else odd "$n"; fi
  count=$((count + 1))
done
[ "$count" -gt 0 ] || die "the converter wrote nothing."

mkdir -p -- "$dest"
chmod 0755 -- "$checked"
mv -T -- "$checked" "$out"
echo "ok: $count file(s) written"
echo "result: $out"
