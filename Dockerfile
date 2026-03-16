# =============================================================================
# inventotrackV2 - Production Dockerfile
# Python 3.12 slim with PostgreSQL support
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Base
# -----------------------------------------------------------------------------
FROM python:3.12-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# -----------------------------------------------------------------------------
# Stage 2: Dependencies (for better caching)
# -----------------------------------------------------------------------------
FROM base as dependencies

# Copy only requirements first (for layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

# -----------------------------------------------------------------------------
# Stage 3: Application
# -----------------------------------------------------------------------------
FROM base as application

# Copy installed dependencies from dependencies stage
COPY --from=dependencies /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=dependencies /usr/local/bin /usr/local/bin

# Copy application code (with owner)
COPY --chown=appuser:appuser . .

# Create directories
RUN mkdir -p /app/static /app/media && \
    chown -R appuser:appuser /app

# CRITICAL: Set execute permissions on entrypoint
RUN chmod +x /app/entrypoint.sh

# Switch to non-root user
USER appuser

# Set environment variables
ENV DJANGO_SETTINGS_MODULE=project.settings.production \
    STATIC_ROOT=/app/static \
    MEDIA_ROOT=/app/media \
    STATIC_URL=/static/ \
    MEDIA_URL=/media/

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--threads", "2", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "project.wsgi:application"]
