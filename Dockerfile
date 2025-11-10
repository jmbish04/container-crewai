# Multi-stage build for Cloudflare Containers
# Platform must be linux/amd64 for Cloudflare compatibility
FROM --platform=linux/amd64 python:3.11-slim-bookworm AS builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv using the official installer for better reliability
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# Copy project config files
COPY pyproject.toml .
COPY uv.lock .

# Install dependencies using uv. Speeds up runtime.
RUN uv sync --no-dev

# Install Playwright browsers
RUN uv run playwright install-deps chromium
RUN uv run playwright install chromium

# Copy application source code
COPY src/ .

# Final stage - smaller image
FROM --platform=linux/amd64 python:3.11-slim-bookworm

WORKDIR /app

# Install Playwright system dependencies in final stage
RUN apt-get update && apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

# Copy uv and installed dependencies from builder
COPY --from=builder /root/.local /root/.local
COPY --from=builder /app /app

ENV PATH="/root/.local/bin:${PATH}"

# Cloudflare Containers and Cloud Run both use PORT environment variable
# Default is 8080 for compatibility with both platforms
ENV PORT 8080
EXPOSE $PORT

# Run the FastAPI application
# Using a single worker for container environments
CMD ["uv", "run", "uvicorn", "api.service:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
