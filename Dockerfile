FROM python:3.13-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy packages
COPY packages/ packages/
COPY pyproject.toml ./

# Install dependencies
RUN uv sync --no-dev

# Expose HTTP API port
EXPOSE 8000

# Set environment variables
ENV OSC_HOST=127.0.0.1
ENV OSC_PORT=57120
ENV API_HOST=0.0.0.0
ENV API_PORT=8000

# Run oiduna
CMD ["uv", "run", "python", "-m", "oiduna_api.main"]
