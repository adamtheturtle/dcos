#!/bin/bash
# Run the self-contained installer inside an isolated Linux PID namespace.
set -euo pipefail
repo_dir=$(cd "$(dirname "$0")/../.." && pwd -P)
checkout_key=$(printf '%s' "$repo_dir" | cksum | awk '{print $1}')
volume=${DCOS_ARM64_VOLUME:-dcos-arm64-$checkout_key}
native_root=$(docker volume inspect "$volume" --format '{{.Mountpoint}}')
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
    -v "$volume:$native_root" -e "NATIVE_ROOT=$native_root" \
    --entrypoint bash dcos/arm64-coordinator:local -c '
        set -euo pipefail
        work=$(mktemp -d "$NATIVE_ROOT/packages/cache/installer-smoke.XXXXXX")
        trap '\''python3 -c "import shutil,sys; shutil.rmtree(sys.argv[1])" "$work"'\'' EXIT
        cd "$work"
        installer="$NATIVE_ROOT/packages/cache/dcos_generate_config.sh"
        bash "$installer" --help
        image=$(python3 -c '\''import re,sys; header=open(sys.argv[1], "rb").read(65536).decode("utf8", "replace"); print(re.search(r"docker images -q ([^ ]+)", header).group(1))'\'' "$installer")
        test "$(docker image inspect "$image" --format '\''{{.Architecture}}'\'')" = arm64
        echo "Self-contained ARM64 installer smoke check passed"
    '
