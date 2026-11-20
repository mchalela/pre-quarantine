#!/usr/bin/env bash
# Build (or rebuild) the tools image. This is the only step that uses the network.
# shellcheck source=tools/_lib.sh
source "$(dirname "$0")/_lib.sh"
# --no-cache: a rebuild has to fetch today's packages. With the cache, docker reuses last month's
# layer for as long as the base image is unchanged, and no security fix arrives.
docker build --pull --no-cache -t "$IMAGE" "$ROOT/tools/image"

# The Alpine branch named in tools/image/Dockerfile gets security fixes until this date
# (https://alpinelinux.org/releases/). Change both together.
SUPPORTED_UNTIL=2028-06-01
if [[ "$(date +%F)" > "$SUPPORTED_UNTIL" ]]; then
  echo "warning: the base of this image stopped getting security fixes on $SUPPORTED_UNTIL." >&2
  echo "         Move tools/image/Dockerfile to a current Alpine branch, then run this again." >&2
fi
