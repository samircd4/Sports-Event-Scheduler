# ─────────────────────────────────────────────────────────────────────────────
# Sports Event Scheduler — Dockerfile
# Uses uv for fast, reproducible Python dependency management.
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.13-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files first (layer-cache friendly)
COPY pyproject.toml uv.lock ./

# Install dependencies into the project venv using the lockfile
RUN uv sync --frozen --no-dev

# Copy the rest of the source code
COPY . .

# Default command: run the scheduler
CMD ["uv", "run", "scheduler.py"]
