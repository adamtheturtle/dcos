# Native ARM64 build work

This work targets Linux ARM64 (`aarch64`), using the upstream `master` branch at
`79b9a39b4e639dc2c9435a869918399b50bfaf24` as its starting point.

The package build path is being brought up on an ARM64 Docker engine. A complete
DC/OS distribution is not yet available from this branch.

## Package builds

From the repository root, run:

```sh
./tools/arm64/build.sh openssl
```

The script builds the native compiler image and a Linux/Python 3.6 coordinator,
then invokes the existing `pkgpanda` recursive package builder. It works with an
ARM64 Linux Docker engine, including Docker Desktop on Apple Silicon. The
wrapper requires at least 10 GiB of free host disk space before it starts.
The repository is mounted at the same absolute path in the coordinator and sibling
build containers. Build images are kept locally.

Use a dedicated checkout and package cache for ARM64 builds. The standard
`packages/cache` layout is retained. Packages containing native executables or
shared libraries are checked for AArch64 ELF headers after a successful build.
This check does not validate libraries embedded inside JARs or archives within
a package, or prove that a DC/OS cluster can run.

To inspect existing package archives:

```sh
python3 tools/arm64/check_elf.py packages/cache/packages/openssl/openssl--*.tar.xz
python3 -m unittest discover -s tools/arm64 -v
```

Packages that use a separate Docker build image still require that image to be
available for ARM64. The wrapper builds the common compiler image only.

## Changes to the compiler and package recipes

* Use a multiarch Ubuntu image for package cleanup.
* Keep Python 2 tooling and AWS CLI on compatible versions.
* Use userspace Linux headers instead of an unavailable pinned kernel-header
  package.
* Build checksum-verified CMake 3.17.0 source on ARM64; retain the existing CMake
  installer on AMD64.
* Select the Go 1.15 archive and checksum for the native architecture.
* Select OpenSSL's native configure target and restore its upstream source URL,
  retaining the original DC/OS source checksum.
* Install the pinned pip source without fetching a modern build backend.
* Resolve native system library paths for Mesos, Admin Router, and conntrack.
* Select the native Glide archive for the DC/OS CNI build.

## Remaining distribution blockers

A source audit on 2026-10-25 found:

| Input | Result |
| --- | --- |
| `downloads.mesosphere.com` | DNS lookup fails; affects Boost, Java, ZooKeeper, strace, the UI update service, and Admin Router's OpenResty mirror. |
| Pinned Marathon archive | GET returns HTTP 403. |
| Pinned Metronome archive | GET returns HTTP 403. |
| CockroachDB 19.1.11 ARM64 archive | HTTP 404 at the corresponding ARM64 download URL. The existing recipe downloads AMD64. |

The distribution also has architecture-specific Java, etcd, Calico and
CockroachDB inputs. Calico's wrapper forces `GOARCH=amd64`; Telegraf downloads an
AMD64 `dep` binary whose release has no corresponding ARM64 asset at that URL.
These require verified ARM64 replacements or source builds. The Admin Router
build image also needs ARM64 work beyond the package's library-copy path.

The pinned scheduler source commits are still available:
[Marathon](https://github.com/mesosphere/marathon/commit/9ee9f3cebb73b1885592a9d634279720bad823cf)
and [Metronome](https://github.com/dcos/metronome/commit/1bcc08cc88cccf4fa4923f64fe008eff0c16837f).
Building replacement distributions from those commits would require restoring
their separate Scala/sbt build environments and validating the resulting JARs.
Those source builds are not implemented by this branch.

Restoring the common compiler image and native core packages does not resolve
these distribution inputs. A full installer build and a cluster smoke test
remain necessary before this branch can claim DC/OS ARM64 support.

## CI

The `Native ARM64 package` GitHub Actions workflow runs on
`ubuntu-24.04-arm`. It builds OpenSSL, libseccomp, Python and the XZ dependency
with the native compiler image, checks their ELF headers, and runs packaged
OpenSSL and Python binaries. The smoke tests check a SHA-256 test vector,
TLS linkage, XZ compression, the ctypes calling convention, Cython extension
import and libseccomp's native architecture identifier.
Successful runs upload the package archives. This workflow validates the core
package build path, not the complete distribution.

## Local verification

On 2026-10-25, the native compiler image and four package archives built locally:

| Package | AArch64 ELF files checked |
| --- | ---: |
| OpenSSL 1.1.1g | 6 |
| libseccomp 2.3.3 | 2 |
| XZ/liblzma 5.2.4 | 5 |
| Python 3.6.8, including Cython 0.29.1 | 71 |

The packaged OpenSSL and Python smoke tests passed. ShellCheck, actionlint,
architecture-check unit tests and `git diff --check` passed. Hosted CI status is
reported separately by the fork's Actions workflow.
