#!/bin/bash
set -euo pipefail
repo_dir=$(cd "$(dirname "$0")/../.." && pwd -P)
smoke_dir=$(mktemp -d)
trap 'python3 -c "import shutil, sys; shutil.rmtree(sys.argv[1])" "$smoke_dir"' EXIT
library_path=''
for package in openssl liblzma libseccomp python; do
    package_id=$(cat "$repo_dir/packages/cache/packages/$package/latest")
    mkdir -p "$smoke_dir/packages/$package_id"
    tar -xJf "$repo_dir/packages/cache/packages/$package/$package_id.tar.xz" \
        -C "$smoke_dir/packages/$package_id"
    library_path="/opt/mesosphere/packages/$package_id/lib:$library_path"
    if [ "$package" = python ]; then
        python_home="/opt/mesosphere/packages/$package_id"
    fi
done
docker run --rm -i --platform linux/arm64 \
    -v "$smoke_dir:/opt/mesosphere:ro" \
    -e "LD_LIBRARY_PATH=$library_path" \
    -e "PYTHONHOME=$python_home" \
    -e "DCOS_PYTHON=$python_home/bin/python3" \
    dcos/dcos-builder:dcos-builder_dockerdir-latest -c 'exec "$DCOS_PYTHON" -' <<'PYTHON'
import ctypes
import lzma
import platform
import ssl
import sys
import Cython
import Cython.Compiler.Scanning

assert platform.machine() == 'aarch64'
assert sys.version_info[:3] == (3, 6, 8)
assert ssl.OPENSSL_VERSION.startswith('OpenSSL 1.1.1g ')
assert lzma.decompress(lzma.compress(b'DC/OS ARM64')) == b'DC/OS ARM64'
libc = ctypes.CDLL(None)
libc.strlen.argtypes = [ctypes.c_char_p]
libc.strlen.restype = ctypes.c_size_t
assert libc.strlen(b'ARM64') == 5
assert Cython.__version__ == '0.29.1'
seccomp = ctypes.CDLL('libseccomp.so.2')
seccomp.seccomp_arch_native.restype = ctypes.c_uint32
assert seccomp.seccomp_arch_native() == 0xc00000b7
print(sys.version)
print(ssl.OPENSSL_VERSION)
print('Native Python, TLS, XZ, ctypes, Cython and libseccomp checks passed')
PYTHON
