FROM python:3.11-slim

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Install uv for fast installs
RUN pip install uv

# Install ALL runtime dependencies directly (avoids hatchling editable install issues)
# Combines: backend deps + shared package transitive deps
RUN uv pip install --system \
    "fastapi>=0.115.0" \
    "uvicorn[standard]>=0.30.0" \
    "pydantic>=2.7.0" \
    "openai>=1.51.0" \
    "anthropic>=0.30.0" \
    "asyncpg>=0.29.0" \
    "python-dotenv>=1.0.0" \
    "opentelemetry-sdk>=1.25.0" \
    "opentelemetry-exporter-otlp-proto-http>=1.25.0" \
    "opentelemetry-instrumentation-httpx>=0.40b0"

# Copy shared packages (source only — imported via PYTHONPATH, not pip-installed)
COPY shared/ ./shared/

# Copy version-b backend
COPY version-b/backend/ ./backend/

# CRITICAL:
#   /workspace/shared  → `from guardrail.service import` works (guardrail/__init__.py)
#                      → `from specialists.classifier import` works
#                      → `from observability.langfuse import` works
#   /workspace         → `from backend.main import` works
ENV PYTHONPATH=/workspace/shared:/workspace

EXPOSE 8001

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8001"]
