FROM calico/node@sha256:dfe680c7f7ecf6b1d8a9160b0c1a8db6b30a9133951c9009b54b72109387f8ed AS calico
FROM dcos/dcos-builder:dcos-builder_dockerdir-latest
# The ARM64 release uses Alpine. Its static runtime binaries run on glibc hosts;
# build the wrapper and libnetwork plugin with the native GNU build environment.
COPY --from=calico /bin/calico-node /bin/calico-node
COPY --from=calico /bin/bird /bin/bird
COPY --from=calico /bin/birdcl /bin/birdcl
COPY --from=calico /etc/calico/confd /etc/calico/confd
RUN /bin/bird --version
