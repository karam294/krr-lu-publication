# Apache Jena Fuseki, built from Apache's own release, pinned and checksummed.
# Replaces the old third-party image stain/jena-fuseki (2026-09-24).
# Verified: this exact server command, with Fuseki 5.5.0 on Java 21, loads and
# answers the Session 2 lab (135,841 triples, all seven questions).
FROM eclipse-temurin:21-jre

ARG FUSEKI_VERSION=5.5.0
ARG FUSEKI_SHA512=bfbf59eac731b71bcf8e148f2abeda9b4adca215639eef3bba61243b308572b23a9a70a43c1483247f9894bfb23d69b59e0e64e1da47cb3cfc592aa979084d5c

ADD https://archive.apache.org/dist/jena/binaries/apache-jena-fuseki-${FUSEKI_VERSION}.tar.gz /tmp/fuseki.tgz
RUN echo "${FUSEKI_SHA512}  /tmp/fuseki.tgz" | sha512sum -c - \
 && mkdir -p /opt/fuseki \
 && tar xzf /tmp/fuseki.tgz -C /opt/fuseki --strip-components=1 \
 && rm /tmp/fuseki.tgz

# Session 4 (D10): the dataset is described in config.ttl instead of on the
# command line, to add one setting: the default graph of a query is the union
# of the named graphs.
COPY config.ttl /opt/fuseki/config.ttl

EXPOSE 3030
# One persistent TDB2 dataset, /kr, open for updates. No login: the port is
# published on localhost only (see docker-compose.yml).
CMD ["sh", "-c", "mkdir -p /data/kr && exec java -jar /opt/fuseki/fuseki-server.jar --port=3030 --config=/opt/fuseki/config.ttl"]
