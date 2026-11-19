#!/usr/bin/env bash
# A throwaway shell for an untrusted repo or extracted folder. No network unless you pass --net.
#   tools/q-shell.sh QUARANTINE/<dir> [--net] [--image python:3.12-slim] [-- command ...]
# shellcheck source=tools/_lib.sh
source "$(dirname "$0")/_lib.sh"
[ $# -ge 1 ] || die "usage: tools/q-shell.sh QUARANTINE/<dir> [--net] [--image IMG]"
d="$(in_quarantine "$1")"; shift; [ -d "$d" ] || die "not a directory"
[[ "$d" =~ ^[A-Za-z0-9._/-]+$ ]] || die "rename the folder first: only letters, digits, . _ - allowed"
net=none; img=python:3.12-slim
cmd=(bash)
while [ $# -gt 0 ]; do case "$1" in
  --net) net=bridge ;; --image) shift; img="${1:?}" ;; --) shift; cmd=("$@"); break ;; *) die "unknown option $1" ;; esac; shift; done
tty=(-i); [ -t 0 ] && tty=(-it)
[ "$net" = bridge ] && echo "!! NETWORK ON: code in this folder can talk to the internet. It still cannot see your home." >&2
exec docker run "${tty[@]}" --rm --network "$net" --cap-drop ALL --security-opt no-new-privileges \
  --user "$(id -u):$(id -g)" --memory 8g --pids-limit 1024 -e HOME=/tmp --tmpfs /tmp:rw,exec,size=4g \
  -v "$d:/work" -w /work "$img" "${cmd[@]}"
