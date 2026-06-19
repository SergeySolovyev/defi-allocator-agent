# Cloud Run container for the human-in-the-loop allocator UI.
#   gcloud run deploy defi-allocator --source . --region europe-west1 --allow-unauthenticated
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY defi_allocator/ ./defi_allocator/
COPY app/ ./app/
COPY data/ ./data/

ENV PORT=8080
EXPOSE 8080
# Cloud Run sets $PORT; bind to it.
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
