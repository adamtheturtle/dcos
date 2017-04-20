class Node:

    def __init__(self):
        self.address = 1

    def run_as_root(self):
        pass


class Cluster:

    def __init__(self):
        self.master = 1
        self.public_agents = set([])
        self.other_agents = set([])


def cluster(config):
    """
    Deploy a cluster with a given config
    """
    pass


class TestExample:

    def test_foo(self):
        config = {}
        cluster(config=config)
