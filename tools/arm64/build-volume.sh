#!/bin/bash
# Internal helper: keep compilation and hard links on a native Linux filesystem.
set -euo pipefail
repo_dir=$(cd "$(dirname "$0")/../.." && pwd -P)
workspace_helper="$repo_dir/tools/arm64/workspace.py"
checkout_key=$(printf '%s' "$repo_dir" | cksum | awk '{print $1}')
volume=${DCOS_ARM64_VOLUME:-dcos-arm64-$checkout_key}
docker volume create "$volume" >/dev/null
native_root=$(docker volume inspect "$volume" --format '{{.Mountpoint}}')
coordinator=dcos/arm64-coordinator:local
mounts=(-v "$volume:$native_root" -v "$workspace_helper:/dcos-workspace.py:ro")
docker run --rm "${mounts[@]}" --entrypoint python3 "$coordinator" -c \
    'import os,sys; os.mkdir(sys.argv[1] + "/.dcos-arm64-build-lock")' "$native_root"
finish() {
    local status=$?
    trap - EXIT
    set +e
    if ! docker run --rm "${mounts[@]}" --entrypoint python3 "$coordinator" \
        /dcos-workspace.py pack-artifacts "$native_root" | \
        python3 "$workspace_helper" unpack-artifacts "$repo_dir"; then status=1; fi
    if ! docker run --rm "${mounts[@]}" --entrypoint python3 "$coordinator" -c \
        'import os,sys; os.rmdir(sys.argv[1] + "/.dcos-arm64-build-lock")' "$native_root"; then status=1; fi
    exit "$status"
}
trap finish EXIT
seed=0
if ! docker run --rm "${mounts[@]}" --entrypoint test "$coordinator" \
    -d "$native_root/packages/cache/packages"; then seed=1; fi
python3 "$workspace_helper" pack-sources "$repo_dir" | \
    docker run --rm -i "${mounts[@]}" --entrypoint python3 "$coordinator" \
    /dcos-workspace.py sync-sources "$native_root"
if [ "$seed" = 1 ]; then
    python3 "$workspace_helper" pack-artifacts "$repo_dir" | \
        docker run --rm -i "${mounts[@]}" --entrypoint python3 "$coordinator" \
        /dcos-workspace.py unpack-artifacts "$native_root"
fi
docker run --rm "${mounts[@]}" --entrypoint mkdir "$coordinator" -p "$native_root/packages/cache"
if [ "$1" = tree ]; then
    docker run --rm --platform linux/arm64 \
        -v /var/run/docker.sock:/var/run/docker.sock -v "$volume:$native_root" \
        -w "$native_root/packages" -e "PYTHONPATH=$native_root" \
        -e "TMPDIR=$native_root/packages/cache" -e "DCOS_BUILD_JOBS=${DCOS_BUILD_JOBS:-2}" \
        "$coordinator" tree --mkbootstrap "--variant=${2:-default}"
else
    for package in "$@"; do
        docker run --rm --platform linux/arm64 \
            -v /var/run/docker.sock:/var/run/docker.sock -v "$volume:$native_root" \
            -w "$native_root/packages/$package" -e "PYTHONPATH=$native_root" \
            -e "TMPDIR=$native_root/packages/cache" -e "DCOS_BUILD_JOBS=${DCOS_BUILD_JOBS:-2}" \
            "$coordinator" --recursive --variant=default
    done
fi
docker run --rm "${mounts[@]}" --entrypoint /bin/bash "$coordinator" -c '
    for archive in "$1"/packages/cache/packages/*/*--*.tar.xz; do
        [ -f "$archive" ] || continue
        case "$archive" in *-tmp.tar.xz) continue ;; esac
        python3 "$1/tools/arm64/check_elf.py" "$archive" || exit
    done
' bash "$native_root"
