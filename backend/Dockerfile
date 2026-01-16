# ============================================
# Knowledge Assistant - Docker Build
# Multi-stage build for optimized production image
# ============================================

# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Pre-download embedding model (for offline deployment)
# This caches the model in the image so no download is needed at runtime
ARG HF_ENDPOINT=https://hf-mirror.com
ENV HF_ENDPOINT=${HF_ENDPOINT}
ENV HF_HOME=/opt/huggingface
ENV TRANSFORMERS_CACHE=/opt/huggingface
COPY scripts/download_model.py /tmp/download_model.py
RUN python /tmp/download_model.py && rm /tmp/download_model.py

# Stage 2: Runtime
FROM python:3.11-slim AS runtime

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 appuser

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Copy pre-downloaded embedding model cache
COPY --from=builder /opt/huggingface /opt/huggingface
ENV HF_HOME=/opt/huggingface
ENV TRANSFORMERS_CACHE=/opt/huggingface
ENV HF_HUB_OFFLINE=1
ENV TRANSFORMERS_OFFLINE=1

# Copy application code
COPY --chown=appuser:appuser . .

# Create data directories
RUN mkdir -p /app/data/uploads /app/data/chroma /app/vault && \
    chown -R appuser:appuser /app/data /app/vault

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
