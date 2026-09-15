FROM python:3.13-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app

COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --upgrade pip setuptools wheel && \
    pip install -e . && \
    pip install "uvicorn[standard]"

FROM python:3.13-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/usr/src/app/src

WORKDIR /usr/src/app

RUN groupadd -r appuser -g 1000 && \
    useradd -r -u 1000 -g appuser -s /bin/bash -d /usr/src/app appuser

COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /usr/src/app/src /usr/src/app/src

RUN mkdir -p /usr/src/app/logs && chown -R appuser:appuser /usr/src/app

USER appuser

EXPOSE 8080

LABEL maintainer="Rahul Sharma <rahul@3embed.com>"

CMD ["python", "-m", "app.main"]
