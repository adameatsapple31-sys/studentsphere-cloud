FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app

RUN addgroup --system app && adduser --system --ingroup app app
USER app

EXPOSE 8000
# Render (and most cloud platforms) tell the app which port to use through $PORT.
# Locally (Docker Compose / Kubernetes) PORT is not set, so it falls back to 8000.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]