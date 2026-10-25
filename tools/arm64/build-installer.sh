#!/bin/bash
# Build and assemble an ARM64 installer locally, without pushing an image.
set -euo pipefail
repo_dir=$(cd "$(dirname "$0")/../.." && pwd -P)
cd "$repo_dir"
checkout_key=$(printf '%s' "$repo_dir" | cksum | awk '{print $1}')
export DCOS_ARM64_VOLUME=${DCOS_ARM64_VOLUME:-dcos-arm64-$checkout_key}
./tools/arm64/build.sh tree default
./tools/arm64/build.sh tree installer
native_root=$(docker volume inspect "$DCOS_ARM64_VOLUME" --format '{{.Mountpoint}}')
bootstrap_root="$native_root/diagnostics/installer-bootstrap"
docker run --rm -v "$DCOS_ARM64_VOLUME:$native_root" \
    -e "NATIVE_ROOT=$native_root" -e "BOOTSTRAP_ROOT=$bootstrap_root" \
    --entrypoint bash dcos/arm64-coordinator:local -c '
        set -e
        id=$(cat "$NATIVE_ROOT/packages/cache/bootstrap/installer.bootstrap.latest")
        mkdir -p "$BOOTSTRAP_ROOT"
        tar -xJf "$NATIVE_ROOT/packages/cache/bootstrap/$id.bootstrap.tar.xz" -C "$BOOTSTRAP_ROOT"
    '
docker run --rm --platform linux/arm64 \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v "$DCOS_ARM64_VOLUME:$native_root" -v "$bootstrap_root:/opt/mesosphere" \
    -w "$native_root" -e "TMPDIR=$native_root/packages/cache" \
    --entrypoint bash dcos/arm64-coordinator:local -c '
        set -e
        source /opt/mesosphere/environment.export
        exec /opt/mesosphere/bin/python3 tools/arm64/assemble_installer.py
    '
docker run --rm -v "$DCOS_ARM64_VOLUME:$native_root" \
    --entrypoint python3 dcos/arm64-coordinator:local \
    "$native_root/tools/arm64/workspace.py" pack-artifacts "$native_root" | \
    python3 tools/arm64/workspace.py unpack-artifacts "$repo_dir"
echo "Installer: $repo_dir/packages/cache/dcos_generate_config.sh"
