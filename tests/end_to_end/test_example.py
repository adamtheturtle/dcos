from subprocess import CalledProcessError

import pytest

from .testtools import Cluster


class TestExample:
    """
    Example tests which demonstrate the features of the test harness.
    """
    def test_martin_example(self) -> None:
        config = {
            'cluster_docker_credentials': {
                'auths': {
                    'https://index.docker.io/v1/': {
                        'auth': 'redacted'
                    },
                },
            },
            'cluster_docker_credentials_enabled': True,
        }

        with Cluster(extra_config=config) as cluster:
            (master, ) = cluster.masters
            master.run_as_root(
                args=[
                    'test',
                    '-f',
                    '/etc/mesosphere/roles/master',
                ]
            )

    def test_file_does_not_exist(self) -> None:
        with Cluster(extra_config={}) as cluster:
            (master, ) = cluster.masters
            with pytest.raises(CalledProcessError):
                master.run_as_root(
                    args=[
                        'test',
                        '-f',
                        '/etc/mesosphere/does_not_exist',
                    ]
                )
