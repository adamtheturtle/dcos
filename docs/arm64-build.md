# Native Linux ARM64 build

This fork starts at DC/OS master `79b9a39b4e639dc2c9435a869918399b50bfaf24`.
The complete native Linux ARM64 installer builds from this branch. Its CLI and
offline configuration generation have passed smoke checks. A full DC/OS cluster
deployment has not been validated. Cloud provisioning templates retain their
upstream image choices; the tested installer targets on-premises Linux ARM64.

## Build

Use an ARM64 Docker engine, including Docker Desktop on Apple Silicon:

```sh
./tools/arm64/build.sh openssl libseccomp python java etcd strace boost-libs dcos-ui-update-service
./tools/arm64/build.sh mesos marathon metronome adminrouter cockroach
./tools/arm64/build-installer.sh
```

The wrapper builds native compiler and coordinator images, then uses pkgpanda's
existing recursive package builder. On macOS it copies sources into a dedicated
Linux Docker volume to support hard links and avoid shared-filesystem compilation
costs. Completed archives are copied back to `packages/cache`; caches survive failed
builds. `DCOS_ARM64_VOLUME` selects a volume explicitly. Concurrent builds in the
same volume are rejected. `DCOS_BUILD_JOBS` defaults to 2; use 1 for Mesos on small
machines. Allow substantial disk space for a full source build; the wrapper refuses
to start with less than 10 GiB free for packages or 50 GiB for the full tree.
Use a separate checkout/cache from AMD64.

Builder images are cached by their input file contents. Set `DCOS_REBUILD_BUILDERS=1`
to rebuild them. Package identities include the selected native source checksums,
compiler image, build recipe and dependency identities.

`architecture_overrides` in buildinfo.json selects complete top-level fields using
`arm64` or `amd64`. The resulting ordinary buildinfo is used by pkgpanda; architecture
metadata is removed before hashing. Sources and single_source are mutually exclusive.

## Restoring retired downloads

The Mesosphere download host no longer resolves, and the original scheduler
archives return 403. Sources with unchanged checksums are restored from upstream
OpenSSL, Boost, AdoptOpenJDK, Apache ZooKeeper, strace and libsodium downloads.
Fluent Bit 1.4.6 uses its checksum-pinned upstream GitHub tag archive because the
old release URL now serves HTML. DC/OS networking uses Rebar 3.16.1, compatible
with the pinned Erlang/OTP 22 and the current Hex registry. Java, etcd and
Calico select verified ARM64 release inputs. CockroachDB is compiled from its pinned
19.1.11 source using a portable RocksDB configuration and native Node/Yarn tools.
The UI update service, Calico libnetwork plugin and Telegraf dependency manager
are compiled from pinned source. Calico uses the static ARM64 binaries from its
digest-pinned release image in a GNU build environment; its ARM64 runtime image
uses Alpine rather than the CentOS image used on AMD64.

The official installer at
<https://downloads.dcos.io/dcos/testing/master/dcos_generate_config.sh> retains
packages built from the exact starting commit. The `installer_package` source
fetcher checks its SHA-1, reads its nested tar archives without executing the
installer or loading its AMD64 image, and verifies the requested package archive's
checksum. Marathon, Metronome and Exhibitor recover their original Java assets;
service files and dependency metadata are regenerated. Marathon and Metronome's
archived buildinfo records exactly the source checksums pinned by this repository.
The installer is shared in a download cache. If the moving upstream URL changes,
the pinned checksum intentionally fails; an archived copy with that checksum is
needed. The recovered archives supply Java application assets; package-level
native executables are compiled or selected for ARM64.

Admin Router copies the original checksum-verified, uncompiled OpenResty and VTS
source bundles from a digest-pinned legacy builder image. The final build image
uses native ARM64 compilers and libraries. The x86-only LuaJIT compiler flag is
omitted for this builder.

## Verification

```sh
python3 -m unittest discover -s tools/arm64 -v
./tools/arm64/smoke_openssl.sh
./tools/arm64/smoke_python.sh
./tools/arm64/smoke_cockroach.sh
./tools/arm64/smoke_adminrouter.sh
./tools/arm64/smoke_schedulers.sh
./tools/arm64/smoke_services.sh
./tools/arm64/smoke_installer.sh  # uses the build volume selected above
python3 tools/arm64/check_elf.py packages/cache/packages/mesos/mesos--*.tar.xz
```

Every completed package is checked for 64-bit AArch64 ELF headers. This detects
accidental AMD64 prebuilts, but does not inspect native objects nested in JARs or
prove cluster operation. Python smoke tests cover TLS, XZ, ctypes, Cython and
libseccomp. Service smoke tests execute Java, etcd, strace and Mesos master/agent.
The bundled Mesos jemalloc 5.0.1 needs the upstream ARM64 pointer fix from
<https://github.com/jemalloc/jemalloc/pull/1035>; without it, high ARM64 virtual
addresses are incorrectly sign extended and Mesos crashes before main. The
backport is applied during the bundled allocator build.

The pinned etcd release requires `ETCD_UNSUPPORTED_ARCH=arm64`, supplied in its
ARM64 package environment.

On 2026-10-25, all 81 distribution packages built successfully. Every selected
archive passed the architecture audit: 491 package-level ELF files are AArch64.
The corrected Mesos master and agent execute and report version 1.11.0.
CockroachDB 19.1.11 starts an in-memory database and answers SQL. Admin Router
serves a LuaJIT HTTP request. Marathon loads the ARM64 Mesos JNI library and
prints its help; Metronome starts against a local ZooKeeper and serves HTTP
`pong`. Erlang runs with the packaged OpenSSL library. The installer bootstrap
passes a native cryptography/CFFI SHA-256 check.

The self-contained `packages/cache/dcos_generate_config.sh` loads its ARM64 Docker
image and executes its CLI successfully. An isolated `--genconf` invocation,
with Docker networking disabled and a temporary static-master configuration,
generated the node installer, configuration packages and cluster package list.
These checks do not constitute a deployed DC/OS cluster test.

GitHub Actions uses `ubuntu-24.04-arm`, checks the source-selection and archive
fetcher/local-source tests, builds native core/service inputs, executes OpenSSL/Python smoke
tests, and uploads the resulting package archives. It does not validate a cluster.
