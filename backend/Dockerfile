FROM python:3.14-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

FROM base AS builder
COPY pyproject.toml ./
RUN mkdir app && touch app/__init__.py && pip install --prefix=/install .

FROM base AS runtime
# The runtime image needs no package manager: removing pip/setuptools drops their (vendored) CVE surface.
RUN python -m pip uninstall -y pip setuptools wheel >/dev/null 2>&1 || true \
    && useradd -r -u 10001 -m appuser && mkdir -p /data/uploads && chown appuser /data/uploads
COPY --from=builder /install /usr/local
COPY --chown=root:root . .
USER appuser
EXPOSE 8000
ENV WEB_CONCURRENCY=4 FORWARDED_ALLOW_IPS=127.0.0.1
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${WEB_CONCURRENCY} --no-access-log --proxy-headers"]
