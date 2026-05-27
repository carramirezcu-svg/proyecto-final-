# ── Build stage ────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Runtime stage ───────────────────────────────────────────────────────────────
FROM python:3.11-slim

LABEL maintainer="DevOps UNAL Manizales"
LABEL version="1.0.0"

# Non-root user
RUN useradd --create-home appuser
WORKDIR /app

COPY --from=builder /install /usr/local
COPY src/app.py .

RUN mkdir -p /app/data && chown appuser:appuser /app/data
USER appuser

ENV PORT=5000
ENV DB_PATH=/app/data/tasks.db

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

CMD ["python", "app.py"]
