# Cloud Run container (root context). `gcloud run deploy --source .` uses THIS.
#   gcloud run deploy defi-allocator --source . --region europe-west1 --allow-unauthenticated
# Slim runtime deps only — Vertex (google-cloud-aiplatform) is optional and
# lazily imported in agent.py; the deployed demo runs without it.
FROM python:3.12-slim

WORKDIR /app
RUN pip install --no-cache-dir \
    "pandas>=2.0" "pyarrow>=14.0" "requests>=2.31" \
    "fastapi>=0.110" "uvicorn[standard]>=0.29" "python-multipart>=0.0.9"

COPY defi_allocator/ ./defi_allocator/
COPY app/ ./app/
COPY data/ ./data/

ENV PORT=8080
EXPOSE 8080
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
