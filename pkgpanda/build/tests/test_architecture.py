import json

import pytest

from pkgpanda.build import BuildError, load_buildinfo


@pytest.mark.parametrize('machine,expected', [('aarch64', 'arm64'), ('arm64', 'arm64'), ('x86_64', 'amd64')])
def test_native_sources(tmpdir, monkeypatch, machine, expected):
    monkeypatch.setattr('pkgpanda.build.platform.machine', lambda: machine)
    info = {
        'requires': ['python'],
        'single_source': {'url': 'amd64', 'sha1': 'original'},
        'architecture_overrides': {'arm64': {'single_source': {'url': 'arm64', 'sha1': 'native'}}},
    }
    tmpdir.join('buildinfo.json').write(json.dumps(info))
    loaded = load_buildinfo(str(tmpdir), None)
    assert loaded['single_source']['url'] == expected
    assert loaded['requires'] == ['python']
    assert 'architecture_overrides' not in loaded


@pytest.mark.parametrize('overrides', [[], {'arm64': []}])
def test_invalid_architecture_overrides(tmpdir, monkeypatch, overrides):
    monkeypatch.setattr('pkgpanda.build.platform.machine', lambda: 'aarch64')
    tmpdir.join('buildinfo.json').write(json.dumps({'architecture_overrides': overrides}))
    with pytest.raises(BuildError):
        load_buildinfo(str(tmpdir), None)
