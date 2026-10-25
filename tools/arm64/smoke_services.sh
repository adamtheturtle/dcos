#!/bin/bash
# Execute the packaged native runtimes with their packaged shared libraries.
set -euo pipefail
repo_dir=$(cd "$(dirname "$0")/../.." && pwd -P)
smoke_dir=$(mktemp -d)
trap 'python3 -c "import shutil, sys; shutil.rmtree(sys.argv[1])" "$smoke_dir"' EXIT
library_path=''
mkdir -p "$smoke_dir/active"
for package in openssl libseccomp liblzma libevent curl boost-libs python java etcd strace mesos; do
    package_id=$(cat "$repo_dir/packages/cache/packages/$package/latest")
    mkdir -p "$smoke_dir/packages/$package_id"
    tar -xJf "$repo_dir/packages/cache/packages/$package/$package_id.tar.xz" \
        -C "$smoke_dir/packages/$package_id"
    ln -s "../packages/$package_id" "$smoke_dir/active/$package"
    library_path="/opt/mesosphere/packages/$package_id/lib:$library_path"
done
docker run --rm --platform linux/arm64 -v "$smoke_dir:/opt/mesosphere:ro" \
    -e "LD_LIBRARY_PATH=$library_path" -e ETCD_UNSUPPORTED_ARCH=arm64 \
    dcos/dcos-builder:dcos-builder_dockerdir-latest -c '
        set -e
        /opt/mesosphere/active/java/usr/java/bin/java -version
        /opt/mesosphere/active/etcd/bin/etcd --version
        /opt/mesosphere/active/strace/bin/strace -V
        /opt/mesosphere/active/mesos/bin/mesos-master --version
        /opt/mesosphere/active/mesos/bin/mesos-agent --version
    '
