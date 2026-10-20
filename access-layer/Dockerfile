# The access layer: serve.py, the TEXT2SPARQL contract (Session 7).
FROM python:3.12-slim
WORKDIR /app/access-layer
COPY access-layer/requirements-access-layer.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements-access-layer.txt
COPY access-layer/ /app/access-layer/
# PYTHONUNBUFFERED: print at once, so docker compose logs shows the server's lines
ENV HOST=0.0.0.0 PORT=8000 PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python", "serve.py"]
