import hashlib
import io
import tarfile

import pytest

from pkgpanda.build.src_fetchers import InstallerPackageSrcFetcher
from pkgpanda.exceptions import ValidationError


def archive(name, data):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w') as output:
        member = tarfile.TarInfo(name)
        member.size = len(data)
        output.addfile(member, io.BytesIO(data))
    return stream.getvalue()


def fetcher(tmp_path, payload=b'portable application bytes'):
    package = 'marathon--' + '1' * 40
    layer = archive('artifacts/packages/marathon/' + package + '.tar.xz', payload)
    image = archive('layer/layer.tar', layer)
    data = b'#!/bin/sh\nexit 99\n#EOF#\n' + archive('genconf.tar', image)
    installer = tmp_path / 'installer.sh'
    installer.write_bytes(data)
    source = InstallerPackageSrcFetcher({
        'kind': 'installer_package', 'url': 'https://example.org/installer.sh',
        'sha1': hashlib.sha1(data).hexdigest(), 'package': package,
        'package_sha1': hashlib.sha1(payload).hexdigest()
    }, str(tmp_path / 'cache/packages/marathon/source'), str(tmp_path))
    return source, installer


def test_recovers_exact_package_without_executing_installer(tmp_path):
    source, installer = fetcher(tmp_path)
    output = tmp_path / 'package.tar.xz'
    source._recover(str(installer), str(output))
    assert output.read_bytes() == b'portable application bytes'
    assert not (source.get_id().keys() & source.info.keys())


def test_missing_package_fails(tmp_path):
    source, installer = fetcher(tmp_path)
    source.info['package'] = 'missing--' + '2' * 40
    with pytest.raises(ValidationError, match='missing'):
        source._recover(str(installer), str(tmp_path / 'output'))


def test_missing_archive_marker_fails(tmp_path):
    source, installer = fetcher(tmp_path)
    installer.write_bytes(b'#!/bin/sh\n')
    with pytest.raises(ValidationError, match='marker'):
        source._recover(str(installer), str(tmp_path / 'output'))


def test_corrupt_package_is_rejected(tmp_path):
    source, installer = fetcher(tmp_path)
    from pathlib import Path
    cache = Path(source.cache)
    cache.mkdir(parents=True)
    (cache / (source.info['sha1'] + '.sh')).write_bytes(installer.read_bytes())
    source.info['package_sha1'] = '0' * 40
    with pytest.raises(ValidationError, match='checksum'):
        source.checkout_to(str(tmp_path / 'destination'))
    assert not list(cache.glob('*.tmp'))
