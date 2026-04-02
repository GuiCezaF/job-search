FROM mcr.microsoft.com/playwright/python:v1.50.0-noble AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3.12-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt .

RUN python3 -m venv --copies /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir -r requirements.txt \
    && mkdir -p /opt/pw-browsers \
    && playwright install chromium

FROM ubuntu:24.04 AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \
    TZ=UTC

COPY --from=builder /opt/venv /opt/venv

ENV PATH="/opt/venv/bin:${PATH}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        tzdata \
        python3.12-minimal \
        libpython3.12-stdlib \
    && ln -snf "/usr/share/zoneinfo/${TZ}" /etc/localtime \
    && echo "${TZ}" > /etc/timezone \
    && /opt/venv/bin/python -m playwright install-deps chromium \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/pw-browsers /opt/pw-browsers

WORKDIR /app
COPY . .
RUN mkdir -p logs output

ENTRYPOINT ["/opt/venv/bin/python", "main.py"]
