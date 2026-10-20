# The learning layer (Session 6) as a one-shot container: build the graph for
# PyTorch Geometric, then the two models. Not part of the stack: run it by hand,
# after the pipeline has written build/graph.nt (docker compose up):
#   docker compose --profile learning run --rm model
FROM python:3.12-slim
WORKDIR /work
COPY model/requirements-model.txt /tmp/
# The CPU build of PyTorch first: from PyPI, Linux gets about 2 GB of GPU libraries.
RUN pip install --no-cache-dir torch==2.8.0 --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir -r /tmp/requirements-model.txt
# The repository is mounted at /work (docker-compose.yml): the results land in
# model/results/ on the host.
CMD ["sh", "-c", "python model/build_graph.py && python model/field.py && python model/coauthors.py"]
