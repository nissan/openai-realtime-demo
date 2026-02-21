FROM python:3.11-slim

WORKDIR /workspace

# Install uv for fast dependency resolution
RUN pip install uv

# Copy shared packages first (for Docker layer caching)
COPY shared/ ./shared/

# Copy version-b backend
COPY version-b/backend/ ./backend/

# Install shared packages as editable + backend deps
# PROJECT_ROOT must be /workspace for pyproject.toml file:// references
ENV PROJECT_ROOT=/workspace
RUN uv pip install --system \
    -e ./shared/guardrail \
    -e ./shared/specialists \
    -e ./shared/observability \
    -e ./backend

# PYTHONPATH so `from backend.xxx import` and `from specialists.xxx import` resolve
ENV PYTHONPATH=/workspace

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
