# End to End tests

End to end tests are tests which require a DC/OS cluster to run against.
Each test spins up at least one cluster, and has the choice of configuring this cluster as appropriate.
For example, a test may require a cluster with a certain number of agents, or certain configuration options.

The tests are agnostic to the backend.
That is, they should pass against clusters on all supported infrastructures.
The current implementation supports only a [DC/OS Docker](https://github.com/dcos/dcos-docker) backend.

## Running tests

The tests must be run on a host which is supported by DC/OS Docker.
One way to guarantee this support is to create a Vagrant VM which supports DC/OS Docker.

```sh
cd tests/end_to_end/
mkdir -p vagrant
cd vagrant
curl -O https://raw.githubusercontent.com/dcos/dcos-docker/master/vagrant/resize-disk.sh
curl -O https://raw.githubusercontent.com/dcos/dcos-docker/master/vagrant/vbox-network.sh
chmod +x resize-disk.sh
chmod +x vbox-network.sh
cd ..
curl -O https://raw.githubusercontent.com/dcos/dcos-docker/master/Vagrantfile
vagrant/resize-disk.sh 102400
vagrant ssh
```

Then when in the environment, install dependencies and enter a `virtualenv`:

```sh
source bootstrap.sh
```

Then run the tests:

```sh
pytest
```

### Options

Copy `sample-configuration.yaml` to `configuration.yaml`.
