FROM python:3.14-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

FROM base AS builder
COPY pyproject.toml ./
RUN mkdir app && touch app/__init__.py && pip install --prefix=/install .

FROM base AS runtime
RUN useradd -r -u 10001 appuser && mkdir -p /data/uploads && chown appuser /data/uploads
COPY --from=builder /install /usr/local
COPY . .
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
