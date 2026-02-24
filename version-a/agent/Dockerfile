# CRITICAL: WORKDIR must be /workspace/agent, PYTHONPATH=/workspace
FROM python:3.11-slim

RUN apt-get update && apt-get install -y build-essential curl && rm -rf /var/lib/apt/lists/*
RUN pip install uv

WORKDIR /workspace

# Copy and install shared packages first
COPY shared/ /workspace/shared/
RUN cd /workspace/shared/guardrail && uv pip install --system -e .
RUN cd /workspace/shared/observability && uv pip install --system -e .
RUN cd /workspace/shared/specialists && uv pip install --system -e .

# Copy and install agent
COPY version-a/agent/ /workspace/agent/
WORKDIR /workspace/agent
RUN uv pip install --system -e .

# CRITICAL: /workspace/shared lets Python find guardrail, observability, specialists
#           /workspace/agent (CWD at runtime) lets Python find agents, models, tools, services
ENV PYTHONPATH=/workspace/shared:/workspace

CMD ["python", "main.py", "start"]
