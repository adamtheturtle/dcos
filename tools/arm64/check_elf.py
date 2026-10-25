#!/usr/bin/env python3
"""Reject foreign ELF binaries in pkgpanda package archives without extracting them."""
import struct
import sys
import tarfile


def check_archive(path):
    count = 0
    errors = []
    with tarfile.open(path, 'r:*') as archive:
        for member in archive:
            if not member.isfile():
                continue
            with archive.extractfile(member) as stream:
                header = stream.read(20)
            if header[:4] != b'\x7fELF':
                continue
            count += 1
            if len(header) < 20 or header[4] != 2 or header[5] not in (1, 2):
                errors.append('{}: invalid or non-64-bit ELF header'.format(member.name))
                continue
            machine = struct.unpack('<H' if header[5] == 1 else '>H', header[18:20])[0]
            if machine != 183:  # EM_AARCH64
                errors.append('{}: ELF machine {} (expected AArch64/183)'.format(member.name, machine))
    return count, errors


def main():
    if len(sys.argv) < 2:
        print('Usage: check_elf.py PACKAGE.tar.xz [...]', file=sys.stderr)
        return 2
    failed = False
    for path in sys.argv[1:]:
        count, errors = check_archive(path)
        print('{}: {} ELF files checked'.format(path, count))
        for error in errors:
            print(error, file=sys.stderr)
        failed = failed or bool(errors)
    return int(failed)


if __name__ == '__main__':
    sys.exit(main())
