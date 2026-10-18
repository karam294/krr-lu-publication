# ROBOT, the OBO community's ontology tool, with the ELK and HermiT reasoners built
# in; pinned and checksummed like fuseki/Dockerfile. The repository is mounted at
# /work (docker-compose.yml), so it always checks the current ontology/ontology.ttl.
#
#   docker compose --profile tools run --rm reasoner                 runs ontology/reason.sh
#   docker compose --profile tools run --rm reasoner robot --help    any other ROBOT command
FROM eclipse-temurin:21-jre

ARG ROBOT_VERSION=1.9.10
ARG ROBOT_SHA256=16a73c074f3df359a7338a84b4e0788785fe06117f931bb9796e9619ea776105

ADD https://github.com/ontodev/robot/releases/download/v${ROBOT_VERSION}/robot.jar /opt/robot/robot.jar
RUN echo "${ROBOT_SHA256}  /opt/robot/robot.jar" | sha256sum -c - \
 && printf '#!/bin/sh\nexec java -jar /opt/robot/robot.jar "$@"\n' > /usr/local/bin/robot \
 && chmod +x /usr/local/bin/robot

WORKDIR /work
# tr removes Windows line endings, so the script runs even when it was saved on Windows.
CMD ["sh", "-c", "tr -d '\\r' < ontology/reason.sh | sh"]