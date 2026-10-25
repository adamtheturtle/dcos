import io
import os
import struct
import tarfile
import tempfile
import unittest

from check_elf import check_archive


class CheckELFTest(unittest.TestCase):
    def check_headers(self, headers):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, 'package.tar.xz')
            with tarfile.open(path, 'w:xz') as archive:
                for name, content in headers.items():
                    member = tarfile.TarInfo(name)
                    member.size = len(content)
                    archive.addfile(member, io.BytesIO(content))
            return check_archive(path)

    @staticmethod
    def elf(machine, bits=2, endian=1):
        return b'\x7fELF' + bytes([bits, endian]) + bytes(12) + struct.pack(
            '<H' if endian == 1 else '>H', machine)

    def test_accept_arm64_and_ignore_text(self):
        count, errors = self.check_headers({'bin/native': self.elf(183), 'bin/script': b'#!/bin/sh\n'})
        self.assertEqual(count, 1)
        self.assertEqual(errors, [])

    def test_reject_x86_64(self):
        count, errors = self.check_headers({'bin/foreign': self.elf(62)})
        self.assertEqual(count, 1)
        self.assertIn('bin/foreign: ELF machine 62', errors[0])

    def test_reject_arm32(self):
        count, errors = self.check_headers({'bin/arm32': self.elf(40, bits=1)})
        self.assertEqual(count, 1)
        self.assertIn('non-64-bit', errors[0])

    def test_read_big_endian_machine(self):
        _, errors = self.check_headers({'bin/foreign': self.elf(62, endian=2)})
        self.assertIn('ELF machine 62', errors[0])


if __name__ == '__main__':
    unittest.main()
