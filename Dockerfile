# =========================
# Stage 1: Builder
# =========================
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Virtualenv
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt


# =========================
# Stage 2: Runtime
# =========================
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Virtualenvni ko‘chiramiz
COPY --from=builder /opt/venv /opt/venv

# www-data user (nginx bilan mos UID)
RUN groupadd -g 33 www-data 2>/dev/null || true && \
    useradd -r -g www-data -u 33 www-data 2>/dev/null || true

WORKDIR /app

# Kodni ko‘chirish
COPY --chown=www-data:www-data . .

# Kerakli papkalar
RUN mkdir -p /app/media /app/staticfiles /app/logs && \
    chown -R www-data:www-data /app && \
    chmod -R 755 /app/media /app/staticfiles

USER www-data

EXPOSE 8000

# Healthcheck (ideal variant)
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Gunicorn (production)
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
