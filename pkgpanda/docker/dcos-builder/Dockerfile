FROM ubuntu:16.04
MAINTAINER help@dcos.io

RUN apt-get -qq update && apt-get -y install \
  autoconf \
  automake \
  autopoint \
  cpp \
  curl \
  default-jdk \
  default-jre \
  dpkg-dev \
  g++-4.8 \
  gcc-4.8 \
  gettext-base \
  git \
  gzip \
  libapr1-dev \
  libc6-dev \
  libcurl4-openssl-dev \
  libnl-3-dev \
  libnl-genl-3-dev \
  libpcre++-dev \
  libpopt-dev \
  libsasl2-dev \
  libsvn-dev \
  libsystemd-dev \
  libtool \
  linux-libc-dev \
  make \
  maven \
  patch \
  pkg-config \
  python-dev \
  python-pip \
  python-setuptools \
  ruby \
  scala \
  unzip \
  wget \
  xutils-dev \
  xz-utils \
  zlib1g-dev \
  bison \
  flex \
  libnfnetlink-dev \
  libmnl-dev \
  libnetfilter-conntrack-dev \
  libnetfilter-cttimeout-dev \
  libnetfilter-cthelper0-dev \
  libnetfilter-queue-dev

ENV CMAKE_VERSION 3.17.0
# CMake 3.17 has no Linux ARM64 binary release. Build the same version
# from verified source on ARM64, retaining the existing AMD64 installer.
RUN set -ex; \
  case "$(dpkg --print-architecture)" in \
    amd64) \
      curl -fsSL https://github.com/Kitware/CMake/releases/download/v${CMAKE_VERSION}/cmake-${CMAKE_VERSION}-Linux-x86_64.sh -o cmake.sh; \
      echo "c20a2878f5f5ca1bc00f0c987b015984360a6b32 cmake.sh" | sha1sum -c -; \
      sh cmake.sh --prefix=/usr/local --skip-license; \
      rm cmake.sh ;; \
    arm64) \
      apt-get install -y libssl-dev; \
      curl -fsSL https://cmake.org/files/v3.17/cmake-${CMAKE_VERSION}.tar.gz -o cmake.tar.gz; \
      echo "b74c05b55115eacc4fa2b77a814981dbda05cdc95a53e279fe16b7b272f00847 cmake.tar.gz" | sha256sum -c -; \
      tar -xzf cmake.tar.gz; \
      cd cmake-${CMAKE_VERSION}; \
      ./bootstrap --prefix=/usr/local --parallel=2 -- -DBUILD_TESTING=OFF; \
      make -j2; \
      make install; \
      cd ..; \
      rm -rf cmake-${CMAKE_VERSION} cmake.tar.gz ;; \
    *) echo "Unsupported build architecture" >&2; exit 1 ;; \
  esac; \
  cmake --version

RUN ln -sf /usr/bin/cpp-4.8 /usr/bin/cpp && \
  ln -sf /usr/bin/g++-4.8 /usr/bin/g++ && \
  ln -sf /usr/bin/gcc-4.8 /usr/bin/gcc && \
  ln -sf /usr/bin/gcc-ar-4.8 /usr/bin/gcc-ar && \
  ln -sf /usr/bin/gcc-nm-4.8 /usr/bin/gcc-nm && \
  ln -sf /usr/bin/gcc-ranlib-4.8 /usr/bin/gcc-ranlib && \
  ln -sf /usr/bin/gcov-4.8 /usr/bin/gcov

ENV GOLANG_VERSION 1.15
RUN set -ex; \
  case "$(dpkg --print-architecture)" in \
    amd64) go_sha256=2d75848ac606061efe52a8068d0e647b35ce487a15bb52272c427df485193602 ;; \
    arm64) go_sha256=7e18d92f61ddf480a4f9a57db09389ae7b9dadf68470d0cb9c00d734a0c57f8d ;; \
    *) echo "Unsupported build architecture" >&2; exit 1 ;; \
  esac; \
  curl -fsSL "https://go.dev/dl/go${GOLANG_VERSION}.linux-$(dpkg --print-architecture).tar.gz" -o golang.tar.gz; \
  echo "$go_sha256  golang.tar.gz" | sha256sum -c -; \
  tar -C /usr/local -xzf golang.tar.gz; \
  rm golang.tar.gz

# Set GOPATH to expected pkgpanda package path for DC/OS
ENV GOPATH /pkg
ENV PATH $GOPATH/bin:/usr/local/go/bin:$PATH

RUN mkdir -p "$GOPATH/src" "$GOPATH/bin" && chmod -R 777 "$GOPATH"

# Xenial ships Python 2 and pip 8, which ignores modern Requires-Python
# metadata. Keep its tooling and AWS CLI on Python-2-compatible versions.
RUN pip install --no-cache-dir --upgrade pip==20.3.4 setuptools==44.1.1 wheel==0.34.2 \
  && pip install --no-cache-dir awscli==1.19.112 PyYAML==5.3.1 \
  && aws --version \
  && cmake --version \
  && go version

ENTRYPOINT ["/bin/bash", "-o", "nounset", "-o", "pipefail", "-o", "errexit"]
