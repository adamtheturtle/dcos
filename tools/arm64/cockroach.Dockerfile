FROM dcos/dcos-builder:dcos-builder_dockerdir-latest
RUN mkdir -p /opt/node /opt/yarn \
    && curl -fsSL https://nodejs.org/dist/v10.15.3/node-v10.15.3-linux-arm64.tar.xz -o /tmp/node.tar.xz \
    && echo '3d7abbf64bffb07c55168ca0f1c17be12b0d93affe9b6cadd39724649215fab9 /tmp/node.tar.xz' | sha256sum -c - \
    && tar -xJf /tmp/node.tar.xz --strip-components=1 -C /opt/node \
    && curl -fsSL https://github.com/yarnpkg/yarn/releases/download/v1.15.2/yarn-v1.15.2.tar.gz -o /tmp/yarn.tar.gz \
    && echo 'c4feca9ba5d6bf1e820e8828609d3de733edf0e4722d17ed7ce493ed39f61abd /tmp/yarn.tar.gz' | sha256sum -c - \
    && tar -xzf /tmp/yarn.tar.gz --strip-components=1 -C /opt/yarn \
    && rm /tmp/node.tar.xz /tmp/yarn.tar.gz
ENV PATH="/opt/node/bin:/opt/yarn/bin:$PATH"
RUN node --version && yarn --version
