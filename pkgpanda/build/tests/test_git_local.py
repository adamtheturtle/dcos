import os
import subprocess

import pytest

from pkgpanda.build.src_fetchers import GitLocalSrcFetcher


@pytest.mark.skipif(not hasattr(os, 'geteuid') or os.geteuid() != 0,
                    reason='Models a root coordinator and a user-owned checkout')
def test_user_owned_local_source_can_be_cloned(tmp_path):
    source = tmp_path / 'source'
    source.mkdir()
    subprocess.check_call(['git', 'init', str(source)])
    (source / 'application.txt').write_text('pinned local source')
    subprocess.check_call(['git', '-C', str(source), 'add', '.'])
    subprocess.check_call(['git', '-C', str(source), '-c', 'user.name=Build Test',
                           '-c', 'user.email=build@example.invalid', 'commit', '-m', 'source'])
    for directory, _, files in os.walk(str(source)):
        os.chown(directory, 501, 501)
        for filename in files:
            os.chown(os.path.join(directory, filename), 501, 501)
    fetcher = GitLocalSrcFetcher({'kind': 'git_local', 'rel_path': 'source'},
                                str(tmp_path / 'cache'), str(tmp_path))
    destination = tmp_path / 'checkout'
    fetcher.checkout_to(str(destination))
    assert (destination / 'application.txt').read_text() == 'pinned local source'
    assert len(fetcher.get_id()['commit']) == 40
