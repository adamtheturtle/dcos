import subprocess
import yaml
from contextlib import ContextDecorator
from pathlib import Path
from typing import Dict, Set

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
    XXX
    """

    def __init__(self, ip_address: str) -> None:
        self.ip_address = ip_address

    def run_as_root(self, args):
        pass


class DCOS_Docker:

    def __init__(self, masters: int, agents: int, public_agents: int,
                 extra_config: Dict) -> None:
        """
        Create a DC/OS Docker cluster
        """
        self._num_masters = masters
        self._num_agents = agents
        self._num_public_agents = public_agents

        self._path = Path('dcos-docker')

        dc_os_docker = 'https://github.com/dcos/dcos-docker.git'

        if not self._path.exists():
            porcelain.clone(dc_os_docker, self._path)

        make_containers_args = [
            "make",
            "MASTERS={masters}".format(masters=masters),
            "AGENTS={agents}".format(agents=agents),
            "PUBLIC_AGENTS={public_agents}".format(public_agents=public_agents),
        ]

        if extra_config:
            extra_genconf = yaml.dump(
                data=extra_config,
                default_flow_style=False,
            )
            extra_genconf_arg = "EXTRA_GENCONF_CONFIG={extra_genconf}".format(
                extra_genconf=extra_genconf)
            make_containers_args.append(extra_genconf_arg)

        subprocess.run(
            args=make_containers_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(self._path),
        )

    def postflight(self) -> None:
        """
        Wait for nodes to be ready to run tests against.
        """
        subprocess.run(
            ['make', 'postflight'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(self._path),
        )

    def destroy(self) -> None:
        """
        Destroy all nodes in the cluster.
        """
        subprocess.run(
            ['make', 'clean'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(self._path),
        )

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

    def __init__(self, extra_config: Dict, masters: int = 1, agents: int = 0,
                 public_agents: int = 0) -> None:
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
    """
    Example tests which demonstrate the features of the test harness.
    """

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
            master.run_as_root(args=['test', '-f', ])
