#!/bin/bash
# Build a package natively on Linux ARM64, including from an Apple Silicon Mac.
set -euo pipefail
repo_dir=$(cd "$(dirname "$0")/../.." && pwd -P)
if [ "$#" -eq 0 ]; then
    echo "Usage: $0 PACKAGE [PACKAGE ...]" >&2
    exit 2
fi
if [ "$1" = tree ]; then
    if [ "$#" -gt 2 ]; then echo "Usage: $0 tree [default|installer]" >&2; exit 2; fi
else
    for package in "$@"; do
        if [ ! -f "$repo_dir/packages/$package/buildinfo.json" ]; then
            echo "Unknown package: $package" >&2
            exit 2
        fi
    done
fi
free_kib=$(df -Pk "$repo_dir" | awk 'NR == 2 {print $4}')
if [ "$free_kib" -lt 10485760 ]; then
    echo 'At least 10 GiB of free host disk space is required before building.' >&2
    exit 1
fi
case "$(docker info --format '{{.Architecture}}')" in
    aarch64|arm64) ;;
    *) echo 'A native ARM64 Docker engine is required.' >&2; exit 1 ;;
esac
# shellcheck source=tools/arm64/builders.sh
source "$repo_dir/tools/arm64/builders.sh"
prepare_builder dcos/dcos-builder:dcos-builder_dockerdir-latest \
    "$repo_dir/pkgpanda/docker/dcos-builder" Dockerfile linux/arm64 Dockerfile README.md
prepare_builder dcos/arm64-coordinator:local "$repo_dir/tools/arm64" Dockerfile linux/arm64 Dockerfile
base_id=$(docker image inspect dcos/dcos-builder:dcos-builder_dockerdir-latest --format '{{.Id}}')
for package in "$@"; do
    # The installer-only tree consists of Python packages, not cluster services.
    if [ "$1" = tree ] && [ "${2:-default}" = installer ]; then break; fi
    case "$package" in
        calico|tree)
            prepare_builder dcos/calico-builder:local "$repo_dir/tools/arm64" calico.Dockerfile \
                "$base_id" calico.Dockerfile ;;
    esac
    case "$package" in
        adminrouter|tree)
            prepare_builder dcos/adminrouter-builder:local "$repo_dir/tools/arm64" adminrouter.Dockerfile \
                "$base_id" adminrouter.Dockerfile build-resty.sh ;;
    esac
    case "$package" in
        cockroach|tree)
            prepare_builder dcos/cockroach-builder:local "$repo_dir/tools/arm64" cockroach.Dockerfile \
                "$base_id" cockroach.Dockerfile ;;
    esac
done
if [ "$(uname -s)" = Darwin ] || [ -n "${DCOS_ARM64_VOLUME:-}" ]; then
    exec "$repo_dir/tools/arm64/build-volume.sh" "$@"
fi
mkdir -p "$repo_dir/packages/cache"
# Keep identical absolute paths inside and outside the coordinator: pkgpanda
# gives these paths to the Docker engine when mounting sibling build containers.
if [ "$1" = tree ]; then
    docker run --rm --platform linux/arm64 \
        -v /var/run/docker.sock:/var/run/docker.sock -v "$repo_dir:$repo_dir" \
        -w "$repo_dir/packages" -e "PYTHONPATH=$repo_dir" \
        -e "TMPDIR=$repo_dir/packages/cache" -e "DCOS_BUILD_JOBS=${DCOS_BUILD_JOBS:-2}" \
        dcos/arm64-coordinator:local tree --mkbootstrap "--variant=${2:-default}"
else
for package in "$@"; do
    docker run --rm --platform linux/arm64 \
        -v /var/run/docker.sock:/var/run/docker.sock \
        -v "$repo_dir:$repo_dir" \
        -w "$repo_dir/packages/$package" \
        -e "PYTHONPATH=$repo_dir" \
        -e "TMPDIR=$repo_dir/packages/cache" \
        -e PYTHONUNBUFFERED=1 \
        -e "DCOS_BUILD_JOBS=${DCOS_BUILD_JOBS:-2}" \
        dcos/arm64-coordinator:local --recursive --variant=default
done
fi
# Audit every dependency built by the recursive invocation, including prebuilts.
for package in "$repo_dir"/packages/cache/packages/*/*--*.tar.xz; do
    [ -f "$package" ] || continue
    case "$package" in *-tmp.tar.xz) continue ;; esac
    python3 "$repo_dir/tools/arm64/check_elf.py" "$package"
done
