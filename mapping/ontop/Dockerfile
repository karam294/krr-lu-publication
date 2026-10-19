# Ontop, the virtualized route (Session 5, D16): a SPARQL endpoint that keeps no
# graph, and answers each query by translating it to SQL on PostgreSQL through
# our R2RML mappings. Ontop 5.5.0 and the PostgreSQL JDBC driver, pinned and
# checksummed like fuseki/Dockerfile and reasoner/Dockerfile.
#
#   docker compose --profile virtual up -d --build ontop     the endpoint, http://127.0.0.1:8080/sparql
#
# The repository is mounted at /work (docker-compose.yml): the endpoint reads
# build/ontop/mapping.ttl and build/ontop/ontop.properties, which
# mapping/ontop/prepare_ontop.py writes.
FROM eclipse-temurin:21-jre

ARG ONTOP_VERSION=5.5.0
ARG ONTOP_SHA256=430dff312e68e8ad41d26e6113160ca2365c28c4fe911926193000a33299458f
ARG JDBC_VERSION=42.7.13
ARG JDBC_SHA256=6e0e4cc2d8cae902084f8a2b18728b073a6fd9d1f87c9d8bff8f298c18185b93

RUN apt-get update && apt-get install -y --no-install-recommends unzip && rm -rf /var/lib/apt/lists/*
ADD https://github.com/ontop/ontop/releases/download/ontop-${ONTOP_VERSION}/ontop-cli-${ONTOP_VERSION}.zip /tmp/ontop.zip
ADD https://github.com/pgjdbc/pgjdbc/releases/download/REL${JDBC_VERSION}/postgresql-${JDBC_VERSION}.jar /tmp/postgresql.jar
RUN echo "${ONTOP_SHA256}  /tmp/ontop.zip" | sha256sum -c - \
 && echo "${JDBC_SHA256}  /tmp/postgresql.jar" | sha256sum -c - \
 && mkdir -p /opt/ontop && unzip -q /tmp/ontop.zip -d /opt/ontop \
 && mv /tmp/postgresql.jar /opt/ontop/jdbc/ \
 && chmod +x /opt/ontop/ontop && rm /tmp/ontop.zip

WORKDIR /work
EXPOSE 8080
CMD ["/opt/ontop/ontop", "endpoint", "-m", "build/ontop/mapping.ttl", "-p", "build/ontop/ontop.properties", "--port", "8080"]
