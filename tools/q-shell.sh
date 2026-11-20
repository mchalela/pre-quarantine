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
  --net) net=pre-quarantine ;;
  --image) [ $# -ge 2 ] || die "--image needs an image name"; shift; img="$1" ;;
  --) shift; cmd=("$@"); break ;;
  *) die "unknown option $1" ;; esac; shift; done
# An image name and nothing else: "--image --volume=/:/host" must never reach docker as an option.
[[ "$img" =~ ^[A-Za-z0-9][A-Za-z0-9._/:@-]*$ ]] || die "not an image name: $img"
tty=(-i); [ -t 0 ] && tty=(-it)
if [ "$net" != none ]; then
  # A network of its own, where containers cannot talk to each other: the code is kept away from
  # whatever else runs in docker on this machine. Docker cannot fence off the host or the LAN.
  docker network inspect "$net" >/dev/null 2>&1 ||
    docker network create --opt com.docker.network.bridge.enable_icc=false "$net" >/dev/null
  echo "!! NETWORK ON: code in this folder can talk to the internet, and also to services on this machine and your local network. It still cannot see your home." >&2
fi
# The label tells the other tools that this folder is in use by code they must not trust.
exec docker run "${tty[@]}" --rm --network "$net" --cap-drop ALL --security-opt no-new-privileges \
  --user "$(id -u):$(id -g)" --memory 8g --memory-swap 8g --pids-limit 1024 -e HOME=/tmp --tmpfs /tmp:rw,exec,size=4g \
  --label "pre-quarantine.shell=$d" -v "$d:/work" -w /work "$img" "${cmd[@]}"
