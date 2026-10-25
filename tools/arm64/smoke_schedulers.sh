#!/bin/bash
set -euo pipefail
repo_dir=$(cd "$(dirname "$0")/../.." && pwd -P)
smoke_dir=$(mktemp -d)
trap 'python3 -c "import shutil, sys; shutil.rmtree(sys.argv[1])" "$smoke_dir"' EXIT
mkdir -p "$smoke_dir/active"
for package in openssl libseccomp liblzma libevent curl boost-libs python java mesos exhibitor marathon metronome; do
    package_id=$(cat "$repo_dir/packages/cache/packages/$package/latest")
    mkdir -p "$smoke_dir/packages/$package_id"
    tar -xJf "$repo_dir/packages/cache/packages/$package/$package_id.tar.xz" \
        -C "$smoke_dir/packages/$package_id"
    ln -s "../packages/$package_id" "$smoke_dir/active/$package"
done
docker run --rm -i --platform linux/arm64 -v "$smoke_dir:/opt/mesosphere:ro" \
    dcos/dcos-builder:dcos-builder_dockerdir-latest -s <<'BASH'
set -euo pipefail
export JAVA_HOME=/opt/mesosphere/active/java/usr/java
library_path=$(find /opt/mesosphere/packages -maxdepth 2 -name lib -type d | paste -sd:)
export LD_LIBRARY_PATH="$library_path"
export MESOS_NATIVE_JAVA_LIBRARY=/opt/mesosphere/active/mesos/lib/libmesos-java.so
"$JAVA_HOME/bin/java" -Xmx256m -XX:ActiveProcessorCount=2 \
    -cp '/opt/mesosphere/active/marathon/marathon/lib/*' \
    mesosphere.marathon.Main --help >/tmp/marathon-help.txt
mkdir -p /tmp/zookeeper
cat > /tmp/zoo.cfg <<'CONFIG'
tickTime=2000
dataDir=/tmp/zookeeper
clientPort=2181
CONFIG
"$JAVA_HOME/bin/java" -Xmx128m -XX:ActiveProcessorCount=2 \
    -cp '/opt/mesosphere/active/exhibitor/usr/zookeeper/zookeeper-3.4.14.jar:/opt/mesosphere/active/exhibitor/usr/zookeeper/lib/*' \
    org.apache.zookeeper.server.quorum.QuorumPeerMain /tmp/zoo.cfg >/tmp/zookeeper.log 2>&1 &
zkpid=$!
METRONOME_MESOS_MASTER_URL=127.0.0.1:5050 METRONOME_ZK_URL=zk://127.0.0.1:2181/metronome \
    /opt/mesosphere/active/metronome/bin/metronome -java-home "$JAVA_HOME" \
    -J-Xms64m -J-Xmx256m -J-XX:ActiveProcessorCount=2 -Dhttp.address=127.0.0.1 -Dhttp.port=9000 \
    >/tmp/metronome.log 2>&1 &
metropid=$!
trap 'kill "$metropid" "$zkpid" 2>/dev/null || true' EXIT
for attempt in $(seq 1 40); do
    if curl -fsS --max-time 2 http://127.0.0.1:9000/ping >/tmp/ping 2>/dev/null; then
        test "$(cat /tmp/ping)" = pong
        echo 'Native Marathon JNI, Metronome and ZooKeeper HTTP smoke checks passed'
        exit 0
    fi
    if ! kill -0 "$metropid" 2>/dev/null; then break; fi
    sleep 1
done
tail -n 70 /tmp/metronome.log
tail -n 15 /tmp/zookeeper.log
exit 1
BASH
