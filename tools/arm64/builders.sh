#!/bin/bash
# Sourced by build.sh. Keep an image stable while its source inputs are unchanged.
builder_script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
prepare_builder() {
    local image=$1 context=$2 dockerfile=$3 salt=$4 key cached
    shift 4
    key=$(python3 "$builder_script_dir/builder_key.py" "$context" "$salt" "$@")
    cached="${image%:*}:arm64-$key"
    if [ "${DCOS_REBUILD_BUILDERS:-0}" = 1 ] || ! docker image inspect "$cached" >/dev/null 2>&1; then
        docker build --platform linux/arm64 -f "$context/$dockerfile" -t "$cached" "$context"
    fi
    docker tag "$cached" "$image"
}
