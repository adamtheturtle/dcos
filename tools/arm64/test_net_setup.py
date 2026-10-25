"""DC/OS networking startup remains idempotent on newer kernels."""

import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch


class NetworkSetupTests(unittest.TestCase):
    def test_existing_addresses_and_real_errors(self):
        path = Path(__file__).resolve().parents[2] / 'packages/dcos-net/extra/dcos-net-setup.py'
        spec = importlib.util.spec_from_file_location('net_setup', str(path))
        setup = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(setup)
        cases = [
            (['ip', 'link', 'add', 'spartan', 'type', 'dummy'],
             b'RTNETLINK answers: File exists\n', 0),
            (['ip', 'addr', 'add', '198.51.100.1/32', 'dev', 'spartan'],
             b'Error: ipv4: Address already assigned.\n', 0),
            (['ip', '-6', 'addr', 'add', 'fd01:d::1/128', 'dev', 'spartan'],
             b'Error: ipv6: address already assigned.\n', 0),
            (['ip', 'addr', 'add', '198.51.100.1/32', 'dev', 'missing'],
             b'Cannot find device "missing"\n', 2),
        ]
        for arguments, stderr, expected in cases:
            with self.subTest(stderr=stderr):
                result = subprocess.CompletedProcess(arguments, 2, stderr=stderr)
                with patch.object(setup, 'run', return_value=result), \
                        patch.object(setup.sys, 'argv', ['setup'] + arguments):
                    with self.assertRaises(SystemExit) as raised:
                        setup.main()
                    self.assertEqual(raised.exception.code, expected)


if __name__ == '__main__':
    unittest.main()
