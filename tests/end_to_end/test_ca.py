import subprocess
import yaml
from contextlib import ContextDecorator
from pathlib import Path

from docker import Client
from dulwich import porcelain

"""
Improvements:

    - Selectable backends
        e.g. AWS
    - Run on CI
    - Move somewhere appropriate
"""


class DCOS_Docker:

    def __init__(self, masters, agents, public_agents, extra_config):
        """
        This can likely be replaced by some kind of upstream.json thing
        """
        self._num_masters = masters
        self._num_agents = agents
        self._public_agents = public_agents

        self._path = Path('dcos-docker')

        dc_os_docker = 'https://github.com/dcos/dcos-docker.git'

        if not self._path.exists():
            porcelain.clone(dc_os_docker, self._path)

        extra_genconf = yaml.dump(
            data=extra_config,
            # This flow style allows us to append the config to the existing config
            default_flow_style=False,
        )

        make_containers = subprocess.Popen(
            [
                "make",
                "-C", str(self._path),
                "EXTRA_GENCONF_CONFIG", extra_genconf,
                "MASTERS", str(masters),
                "AGENTS", str(agents),
                "PUBLIC_AGENTS", str(public_agents),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        result = make_containers.wait()

        if result != 0:
            stdout, stderr = make_containers.communicate()
            import pdb; pdb.set_trace()
            pass

    def postflight(self):
        postflight_command = subprocess.Popen(
            [
                "make",
                "-C", str(self._path),
                "postflight",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        postflight_command.wait()

    def destroy_nodes(self):
        pass

    @property
    def masters(self):
        client = Client()
        nodes = set()

        for master_number in range(1, self._num_masters + 1):
            container_name = 'dcos-docker-master' + master_number
            details = client.inspect_container(container=container_name)
            ip_address = details['NetworkSettings']['IPAddress']
            node = Node(ip_address=ip_address)
            nodes.add(node)

        return nodes


class Node:

    def __init__(self, ip_address):
        self.ip_address = ip_address

    def run_as_root(self):
        pass


class Cluster(ContextDecorator):

    def __init__(self, extra_config, masters=1, agents=1, public_agents=1):
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
    def masters(self):
        return self._backend.masters

    @property
    def agents(self):
        return self._backend.agents

    @property
    def public_agents(self):
        return self._backend.public_agents

    def __exit__(self, *exc):
        self._backend.destroy_nodes()


class TestExample:

    def test_foo(self):
        config = {}
        with Cluster(extra_config=config) as cluster:
            import pdb; pdb.set_trace()
            pass
