import subprocess
import yaml
from contextlib import ContextDecorator
from pathlib import Path
from typing import Dict, List, Set, Tuple

from docker import Client
from dulwich import porcelain
"""
Improvements:

    - Selectable backends e.g. AWS
    - Run on CI
        - Currently this just downloads the latest `master`.  On CI and
        locally, we want to run against the current build.
    - Move somewhere appropriate
        - This is just in a new directory in DC/OS but it should maybe be in
        DC/OS-E or somewhere else in DC/OS.
    - Instead of cloning DC/OS Docker, instead use a more appropriate system
        (e.g. upstream.json)
"""


class Node:
    """
    A record of a DC/OS cluster node.
    """

    def __init__(self, ip_address: str) -> None:
        self.ip_address = ip_address

    def run(self, args: List[str]) -> None:
        pass


class DCOS_Docker:
    """
    A record of a DC/OS Docker cluster.
    """

    def __init__(
        self,
        masters: int,
        agents: int,
        public_agents: int,
        extra_config: Dict
    ) -> None:
        """
        Create a DC/OS Docker cluster
        """
        self._masters = masters
        self._agents = agents
        self._public_agents = public_agents

        self._path = Path('dcos-docker')

        dc_os_docker = 'https://github.com/dcos/dcos-docker.git'

        if not self._path.exists():
            porcelain.clone(dc_os_docker, self._path)

        make_containers_args = {
            'MASTERS': masters,
            'AGENTS': agents,
            'PUBLIC_AGENTS': public_agents,
        }

        if extra_config:
            make_containers_args['EXTRA_GENCONF_CONFIG'] = yaml.dump(
                data=extra_config,
                default_flow_style=False,
            )

        args = ['make'] + [
            '{key}={value}'.format(key=key, value=value)
            for key, value in make_containers_args.items()
        ]
        subprocess.run(args=args, cwd=str(self._path))

    def postflight(self) -> None:
        """
        Wait for nodes to be ready to run tests against.
        """
        subprocess.run(args=['make', 'postflight'], cwd=str(self._path))

    def destroy(self) -> None:
        """
        Destroy all nodes in the cluster.
        """
        subprocess.run(args=['make', 'clean'], cwd=str(self._path))

    def _nodes(self, container_base_name: str, num_nodes: int) -> Set[Node]:
        """
        Args:
            container_base_name: The start of the container names.
            num_nodes: The number of nodes.

        Returns: ``Node``s corresponding to containers with names starting
            with ``container_base_name``.
        """
        client = Client()
        nodes = set([])  # type: Set[Node]

        while len(nodes) < num_nodes:
            container_name = '{container_base_name}{number}'.format(
                container_base_name=container_base_name,
                number=len(nodes) + 1,
            )
            details = client.inspect_container(container=container_name)
            ip_address = details['NetworkSettings']['IPAddress']
            node = Node(ip_address=ip_address)
            nodes.add(node)

        return nodes

    @property
    def masters(self) -> Set[Node]:
        return self._nodes(
            container_base_name='dcos-docker-master',
            num_nodes=self._masters,
        )


class Cluster(ContextDecorator):
    """
    A record of a DC/OS Cluster.

    This is intended to be used as context manager.
    """

    def __init__(
        self,
        extra_config: Dict,
        masters: int=1,
        agents: int=0,
        public_agents: int=0
    ) -> None:
        self._backend = DCOS_Docker(
            masters=masters,
            agents=agents,
            public_agents=public_agents,
            extra_config=extra_config,
        )
        self._backend.postflight()

    def __enter__(self) -> 'Cluster':
        return self

    @property
    def masters(self) -> Set[Node]:
        return self._backend.masters

    def __exit__(self, *exc: Tuple[None, None, None]) -> bool:
        """
        On exiting, destroy all nodes in the cluster.
        """
        self._backend.destroy()
        return False


class TestExample:
    """
    Example tests which demonstrate the features of the test harness.
    """

    def test_empty_config(self) -> None:
        with Cluster(extra_config={}) as cluster:
            (master, ) = cluster.masters

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
            master.run(args=[
                'test',
                '-f',
            ])
