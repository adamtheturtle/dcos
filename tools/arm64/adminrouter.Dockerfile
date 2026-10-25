# The original build image retains the checksum-verified, uncompiled OpenResty
# bundle whose Mesosphere download host has disappeared. Copy sources only.
FROM --platform=linux/amd64 dcos/dcos-builder@sha256:0876e941ec3bcaa37d3f9150fbc467dbafcae19ebb1e3295e6378ed350168ebb AS archived
FROM dcos/dcos-builder:dcos-builder_dockerdir-latest
RUN apt-get update && apt-get install -y --no-install-recommends libpcre3-dev \
    && rm -rf /var/lib/apt/lists/*
COPY --from=archived /usr/local/src/openresty /usr/local/src/openresty
COPY --from=archived /usr/local/src/jongiddy-nginx-module-vts-3686706 /usr/local/src/jongiddy-nginx-module-vts-3686706
COPY build-resty.sh /usr/local/src/build-resty.sh
ENV OPENRESTY_DIR=/usr/local/src/openresty \
    OPENRESTY_COMPILE_SCRIPT=/usr/local/src/build-resty.sh \
    VTS_MODULE_DIR=/usr/local/src/jongiddy-nginx-module-vts-3686706
