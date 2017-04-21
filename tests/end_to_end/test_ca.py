import subprocess
import yaml
from contextlib import ContextDecorator
from pathlib import Path
from typing import Dict, Set

import pytest
from docker import Client
from dulwich import porcelain


"""
Improvements:

    - Selectable backends
        e.g. AWS
    - Run on CI
    - Move somewhere appropriate
"""


class Node:
    """
    XXX
    """

    def __init__(self, ip_address: str) -> None:
        self.ip_address = ip_address

    def run_as_root(self):
        pass


class DCOS_Docker:

    def __init__(self, masters: int, agents: int, public_agents: int,
                 extra_config: Dict) -> None:
        """
        This can likely be replaced by some kind of upstream.json thing
        """
        self._num_masters = masters
        self._num_agents = agents
        self._num_public_agents = public_agents

        self._path = Path('dcos-docker')

        dc_os_docker = 'https://github.com/dcos/dcos-docker.git'

        if not self._path.exists():
            porcelain.clone(dc_os_docker, self._path)

        extra_genconf = yaml.dump(
            data=extra_config,
            default_flow_style=False,
        )

        if not extra_config:
            # Adding {} to the end of the config confuses the parser
            extra_genconf = ''

        make_containers = subprocess.Popen(
            [
                "make",
                "EXTRA_GENCONF_CONFIG={extra_genconf}".format(
                    extra_genconf=extra_genconf),
                "MASTERS={masters}".format(masters=masters),
                "AGENTS={agents}".format(agents=agents),
                "PUBLIC_AGENTS={public_agents}".format(public_agents=public_agents),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(self._path),
        )

        result = make_containers.wait()

        if result != 0:
            import pdb; pdb.set_trace()
            stdout, stderr = make_containers.communicate()
            raise Exception(stderr)

    def postflight(self) -> None:
        """
        Wait for nodes to be ready to run tests against.
        """
        postflight_command = subprocess.Popen(
            ['make', 'postflight'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(self._path),
        )

        postflight_command.wait()

    def destroy(self) -> None:
        """
        Destroy all nodes in the cluster.
        """
        clean_command = subprocess.Popen(
            ['make', 'clean'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(self._path),
        )

        clean_command.wait()

    def _nodes(self, container_base_name: str,
               num_containers: int) -> Set[Node]:
        """
        XXX
        """
        client = Client()
        nodes = set()

        for container_number in range(1, num_containers + 1):
            container_name = '{container_base_name}{number}'.format(
                container_base_name=container_base_name,
                number=container_number)
            details = client.inspect_container(container=container_name)
            ip_address = details['NetworkSettings']['IPAddress']
            node = Node(ip_address=ip_address)
            nodes.add(node)

        return nodes

    @property
    def masters(self) -> Set[Node]:
        return self._nodes(
            container_base_name='dcos-docker-master',
            num_containers=self._num_masters,
        )

    @property
    def agents(self) -> Set[Node]:
        return self._nodes(
            container_base_name='dcos-docker-agent',
            num_containers=self._num_agents,
        )

    @property
    def public_agents(self) -> Set[Node]:
        return self._nodes(
            container_base_name='dcos-docker-pubagent',
            num_containers=self._num_public_agents,
        )


class Cluster(ContextDecorator):

    def __init__(self, extra_config: Dict, masters: int = 1, agents: int = 1,
                 public_agents: int = 1) -> None:
        self._backend = DCOS_Docker(
            masters=masters,
            agents=agents,
            public_agents=public_agents,
            extra_config=extra_config,
        )
        self._backend.postflight()

    def __enter__(self):
        return self

    @property
    def masters(self) -> Set[Node]:
        return self._backend.masters

    @property
    def agents(self) -> Set[Node]:
        return self._backend.agents

    @property
    def public_agents(self) -> Set[Node]:
        return self._backend.public_agents

    def __exit__(self, *exc) -> None:
        self._backend.destroy()


class TestExample:

    def test_empty_config(self) -> None:
        with Cluster(extra_config={}) as cluster:
            (master,) = cluster.masters

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
            (master,) = cluster.masters
