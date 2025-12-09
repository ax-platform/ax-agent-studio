# Lightweight Python base (safer than 3.14 bleeding edge)
FROM python:3.12-slim

WORKDIR /app

# Best practice: Don't run as root
# Combined layers to reduce image size
RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/* && \
    useradd -m -u 1000 appuser && \
    mkdir -p /app/artifacts && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Copy scripts with correct ownership
COPY --chown=appuser:appuser scripts/ /app/scripts/

# Ensure executable
RUN chmod +x /app/scripts/diagnose_env.sh

ENTRYPOINT ["/app/scripts/diagnose_env.sh"]
