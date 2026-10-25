#!/bin/bash
set -euo pipefail
repo_dir=$(cd "$(dirname "$0")/../.." && pwd -P)
package_id=$(cat "$repo_dir/packages/cache/packages/cockroach/latest")
smoke_dir=$(mktemp -d)
trap 'python3 -c "import shutil, sys; shutil.rmtree(sys.argv[1])" "$smoke_dir"' EXIT
tar -xJf "$repo_dir/packages/cache/packages/cockroach/$package_id.tar.xz" -C "$smoke_dir"
docker run --rm --platform linux/arm64 -v "$smoke_dir:/cockroach:ro" \
    -e GOMAXPROCS=2 dcos/dcos-builder:dcos-builder_dockerdir-latest -c '
        set -e
        binary=/cockroach/bin/cockroach
        "$binary" version
        "$binary" start --insecure --store=type=mem,size=1GiB \
            --cache=64MiB --max-sql-memory=64MiB --listen-addr=127.0.0.1:26257 \
            --http-addr=127.0.0.1:8080 --background --pid-file=/tmp/cockroach.pid \
            --log-dir=/tmp/cockroach-logs >/tmp/cockroach-start.log 2>&1 || {
                cat /tmp/cockroach-start.log
                exit 1
            }
        trap '\''kill "$(cat /tmp/cockroach.pid)"'\'' EXIT
        result=$("$binary" sql --insecure --host=127.0.0.1:26257 --format=tsv \
            -e "SELECT 6 * 7 AS answer")
        printf "%s\n" "$result"
        test "$(printf "%s\n" "$result" | tail -n 1)" = 42
    '
