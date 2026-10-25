"""Assemble the local installer using the existing generator, without publishing."""
import json
from pathlib import Path

from gen.build_deploy.bash import make_installer_docker


def main():
    cache = Path('packages/cache/complete')
    distribution = json.loads((cache / 'complete.latest.json').read_text())
    installer = json.loads((cache / 'installer.complete.latest.json').read_text())
    filename = make_installer_docker(None, distribution, installer)
    print('Created ' + filename)


if __name__ == '__main__':
    main()
