#!/bin/bash
# Build a package natively on Linux ARM64, including from an Apple Silicon Mac.
set -euo pipefail
repo_dir=$(cd "$(dirname "$0")/../.." && pwd -P)
if [ "$#" -eq 0 ]; then
    echo "Usage: $0 PACKAGE [PACKAGE ...]" >&2
    exit 2
fi
for package in "$@"; do
    if [ ! -f "$repo_dir/packages/$package/buildinfo.json" ]; then
        echo "Unknown package: $package" >&2
        exit 2
    fi
done
free_kib=$(df -Pk "$repo_dir" | awk 'NR == 2 {print $4}')
if [ "$free_kib" -lt 10485760 ]; then
    echo 'At least 10 GiB of free host disk space is required before building.' >&2
    exit 1
fi
case "$(docker info --format '{{.Architecture}}')" in
    aarch64|arm64) ;;
    *) echo 'A native ARM64 Docker engine is required.' >&2; exit 1 ;;
esac
docker build --platform linux/arm64 \
    -t dcos/dcos-builder:dcos-builder_dockerdir-latest \
    "$repo_dir/pkgpanda/docker/dcos-builder"
docker build --platform linux/arm64 \
    -t dcos/arm64-coordinator:local "$repo_dir/tools/arm64"
mkdir -p "$repo_dir/packages/cache"
# Keep identical absolute paths inside and outside the coordinator: pkgpanda
# gives these paths to the Docker engine when mounting sibling build containers.
for package in "$@"; do
    docker run --rm --platform linux/arm64 \
        -v /var/run/docker.sock:/var/run/docker.sock \
        -v "$repo_dir:$repo_dir" \
        -w "$repo_dir/packages/$package" \
        -e "PYTHONPATH=$repo_dir" \
        -e "TMPDIR=$repo_dir/packages/cache" \
        -e PYTHONUNBUFFERED=1 \
        dcos/arm64-coordinator:local --recursive --variant=default
done
# Audit every dependency built by the recursive invocation, including prebuilts.
for package in "$repo_dir"/packages/cache/packages/*/*--*.tar.xz; do
    [ -f "$package" ] || continue
    case "$package" in *-tmp.tar.xz) continue ;; esac
    python3 "$repo_dir/tools/arm64/check_elf.py" "$package"
done
