#!/bin/bash
set -euo pipefail
repo_dir=$(cd "$(dirname "$0")/../.." && pwd -P)
package_id=$(cat "$repo_dir/packages/cache/packages/openssl/latest")
archive="$repo_dir/packages/cache/packages/openssl/$package_id.tar.xz"
smoke_dir=$(mktemp -d)
trap 'python3 -c "import shutil, sys; shutil.rmtree(sys.argv[1])" "$smoke_dir"' EXIT
tar -xJf "$archive" -C "$smoke_dir"
package_path="/opt/mesosphere/packages/$package_id"
docker run --rm --platform linux/arm64 \
    -v "$smoke_dir:$package_path:ro" \
    -e "LD_LIBRARY_PATH=$package_path/lib" \
    -e "OPENSSL=$package_path/bin/openssl" \
    dcos/dcos-builder:dcos-builder_dockerdir-latest -c '
        "$OPENSSL" version
        digest=$(printf abc | "$OPENSSL" dgst -sha256 | awk "{print \$NF}")
        test "$digest" = ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad
    '
