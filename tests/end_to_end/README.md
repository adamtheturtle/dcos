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
# Update the kernel and re-provision to work around
# https://github.com/moby/moby/issues/5618
vagrant ssh -c 'sudo yum update -y kernel'
vagrant reload
vagrant provision
vagrant ssh
```

Then when in the environment, install dependencies and enter a `virtualenv`:

```sh
source bootstrap.sh
```

Then set the test options.
See "Options".

Then run the tests:

```sh
pytest
```

### Options

Configuration options are specified in `sample-configuration.yaml`.
Copy this file to `configuration.yaml` and fill it in as appropriate.
Values with `null` in the sample configuration are not required.

The DC/OS Docker clone should be in a location which the tests can write to.
In the Vagrant development environment, `/tmp/dcos-docker` is a suitable place.
This directory may be interfered with by the tests.

Postflight checks to see if DC/OS is ready do not work for DC/OS Enterprise.
See <https://jira.mesosphere.com/browse/DCOS-15322>.
As a workaround, use a particular fork of `DC/OS Docker`
until <https://github.com/dcos/dcos-docker/pull/34> is merged:

```sh
git clone -b dcos-enterprise-postflight-DCOS-15322 https://github.com/adamtheturtle/dcos-docker.git
```

# Discussion and future

## Selectable backends

I can imagine that in the future this tool will need to be run on different backends.
Therefore I have tried to abstract `Cluster` from DC/OS Docker.
Discuss with Daniel Baker the overlap between this tool and future plans.

## Options passing

This POC uses a `configuration.yaml` file.
Other options include command line options and environment variables.
I can imagine this getting very unweildy.
Similar high level test tools which I have worked on have grown to allow a very large number of options and I believe that this could be the case here.

## Where these tests live

These tests are currently in their own directory with their own requirements and such.

This could be moved to DCOS-E, or somewhere else in DCOS-OSS.

We should when these tests are run.
E.g. on every build on CI, nightly, etc.

This also brings in discussion about where the debug output should go.

## How these tests get DC/OS Docker

This could clone DC/OS Docker.
This could use somethink like `pkgpanda`.
This could continue as-is - using a path to an existing clone.

## Style checking

For development help I used mypy and YAPF.
I committed the configs.
Where and whether they live should be discussed.

## Parallelisation

These tests are very slow and they should be very parallelisable.
However, that may require some changes as currently DC/OS Docker names containers in a deterministic manner.
That is, you can't spin up two DC/OS Docker clusters simultaneously right now.
