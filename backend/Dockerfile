# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MIMI_DB_PATH=/data/mimi.db

WORKDIR /app
COPY backend/pyproject.toml backend/README.md ./backend/
COPY backend/mimi ./backend/mimi

RUN --mount=type=secret,id=proxy_ca,target=/run/secrets/proxy_ca,required=false \
    --mount=type=secret,id=system_ca,target=/run/secrets/system_ca,required=false \
    set -e; \
    if [ -f /run/secrets/proxy_ca ]; then \
      if [ -f /run/secrets/system_ca ]; then \
        cat /run/secrets/system_ca /run/secrets/proxy_ca > /tmp/mimi-ca.pem; \
      else \
        cat /etc/ssl/certs/ca-certificates.crt /run/secrets/proxy_ca > /tmp/mimi-ca.pem; \
      fi; \
      PIP_CERT=/tmp/mimi-ca.pem pip install --no-cache-dir ./backend; \
      rm -f /tmp/mimi-ca.pem; \
    else \
      pip install --no-cache-dir ./backend; \
    fi \
    && useradd --system --no-create-home --shell /usr/sbin/nologin mimi \
    && mkdir -p /data \
    && chown mimi:mimi /data

USER mimi
EXPOSE 8000
CMD ["uvicorn", "mimi.api:app", "--host", "0.0.0.0", "--port", "8000"]
