# Build stage
FROM python:3.12-slim AS builder

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.12-slim AS runner

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends fonts-dejavu-core && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd --system --gid 1001 appgroup && \
    useradd --system --uid 1001 --gid appgroup appgroup

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=appgroup:appgroup . .

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh
RUN mkdir -p /app/uploads /app/private/certificates && chown -R appgroup:appgroup /app/uploads /app/private

# Switch to non-root user
USER appgroup

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run via entrypoint script (waits for DB, runs migrations, starts app)
CMD ["/app/entrypoint.sh"]
