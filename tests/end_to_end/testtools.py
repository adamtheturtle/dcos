import os
import shutil
import subprocess
import time
import yaml
from contextlib import ContextDecorator
from pathlib import Path
from tempfile import mkdtemp
from typing import Dict, List, Set, Tuple

from docker import Client
from dulwich import porcelain
"""
Potential improvements:

    - Selectable backends e.g. AWS
    - Run on CI
        - Currently this just downloads the latest `master`.  On CI and
        locally, we want to run against the current build.
    - Move somewhere appropriate
        - This is just in a new directory in DC/OS but it should maybe be in
        DC/OS-E or somewhere else in DC/OS.
    - Instead of cloning DC/OS Docker, instead use a more appropriate system
        (e.g. upstream.json)
    - Log command output properly
"""


class Node:
    """
    A record of a DC/OS cluster node.
    """

    def __init__(self, ip_address: str, ssh_key_path: Path) -> None:
        self._ip_address = ip_address
        self._ssh_key_path = ssh_key_path

    def run_as_root(self, args: List[str]) -> subprocess.CompletedProcess:
        """
        Run a command on this ``Node``.

        Args:
            The command to run on the ``Node``.

        Returns:
            The representation of the finished process.

        Raises:
            CalledProcessError: The process exited with a non-zero code.
        """
        ssh_args = [
            'ssh',
            # Suppress warnings.
            # In particular, we don't care about remote host identification
            # changes.
            "-q",
            # The node may be an unknown host.
            "-o",
            "StrictHostKeyChecking=no",
            # Use an SSH key which is authorized.
            "-i",
            str(self._ssh_key_path),
            # Run commands as the root user.
            "-l",
            "root",
            # Bypass password checking.
            "-o",
            "PreferredAuthentications=publickey",
            self._ip_address,
        ] + args

        subprocess.run(args=ssh_args, check=True)


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

        # We clone in the directory containing this file as we need write
        # permissions, for example to delete the directory.
        file_dir = os.path.dirname(os.path.realpath(__file__))
        clone_dir = mkdtemp(dir=file_dir)
        self._path = Path(clone_dir)

        porcelain.clone(
            source='https://github.com/dcos/dcos-docker.git',
            target=str(self._path),
        )

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
        subprocess.run(args=args, cwd=str(self._path), check=True)

    def postflight(self) -> None:
        """
        Wait for nodes to be ready to run tests against.
        """
        enterprise = False
        if enterprise:
            time.sleep(8 * 60)
        else:
            subprocess.run(
                args=['make', 'postflight'], cwd=str(self._path), check=True
            )

    def destroy(self) -> None:
        """
        Destroy all nodes in the cluster.
        """
        subprocess.run(args=['make', 'clean'], cwd=str(self._path), check=True)
        shutil.rmtree(path=str(self._path))

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
            node = Node(
                ip_address=ip_address,
                ssh_key_path=self._path / 'include' / 'ssh' / 'id_rsa',
            )
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
