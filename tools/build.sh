#!/usr/bin/env bash
# Build (or rebuild) the tools image. This is the only step that uses the network.
source "$(dirname "$0")/_lib.sh"
docker build --pull -t "$IMAGE" "$ROOT/tools/image"
