#!/bin/bash
set -euo pipefail
repo_dir=$(cd "$(dirname "$0")/../.." && pwd -P)
smoke_dir=$(mktemp -d)
trap 'python3 -c "import shutil, sys; shutil.rmtree(sys.argv[1])" "$smoke_dir"' EXIT
library_path=''
for package in openssl adminrouter; do
    package_id=$(cat "$repo_dir/packages/cache/packages/$package/latest")
    mkdir -p "$smoke_dir/packages/$package_id"
    tar -xJf "$repo_dir/packages/cache/packages/$package/$package_id.tar.xz" \
        -C "$smoke_dir/packages/$package_id"
    library_path="/opt/mesosphere/packages/$package_id/lib:/opt/mesosphere/packages/$package_id/luajit/lib:$library_path"
    if [ "$package" = adminrouter ]; then nginx="/opt/mesosphere/packages/$package_id/nginx/sbin/nginx"; fi
done
docker run --rm -i --platform linux/arm64 -v "$smoke_dir:/opt/mesosphere:ro" \
    -e "LD_LIBRARY_PATH=$library_path" -e "DCOS_NGINX=$nginx" \
    dcos/dcos-builder:dcos-builder_dockerdir-latest -s <<'BASH'
set -euo pipefail
"$DCOS_NGINX" -V
mkdir -p /tmp/nginx/logs
cat > /tmp/nginx.conf <<'CONFIG'
pid /tmp/nginx.pid;
events {}
http {
    server {
        listen 127.0.0.1:18080;
        location / {
            content_by_lua_block {
                local total = 0
                for i = 1, 1000 do total = total + i end
                ngx.say(total)
            }
        }
    }
}
CONFIG
"$DCOS_NGINX" -p /tmp/nginx -c /tmp/nginx.conf
trap '"$DCOS_NGINX" -p /tmp/nginx -c /tmp/nginx.conf -s stop' EXIT
response=$(curl -fsS http://127.0.0.1:18080/)
test "$response" = 500500
printf 'Native OpenResty and LuaJIT HTTP smoke check passed: %s\n' "$response"
BASH
