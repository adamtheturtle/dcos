# The build coordinator needs Linux filesystem tools and Python 3.6.
# Package compilation runs in sibling containers via the mounted Docker socket.
FROM docker:29-cli AS docker-cli
FROM ubuntu:18.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl git build-essential libffi-dev libssl-dev \
    python3 python3-dev python3-pip python3-venv tar unzip xz-utils \
    && rm -rf /var/lib/apt/lists/*
COPY --from=docker-cli /usr/local/bin/docker /usr/local/bin/docker
RUN python3 -m pip install --no-cache-dir \
    pip==21.3.1 setuptools==59.6.0 wheel==0.37.1
RUN python3 -m pip install --no-cache-dir \
    requests==2.24.0 retrying==1.3.3 PyYAML==5.3.1 \
    teamcity-messages==1.32 schema==0.7.4 docopt==0.6.2 pytest==5.4.3
ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python3", "-m", "pkgpanda.build.cli"]
