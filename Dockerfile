FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry

# Copy dependency files
COPY pyproject.toml README.md ./

# Configure poetry to not create a virtual environment inside the container
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

# Copy code
COPY mcp_server.py ./
COPY powerbi/ ./powerbi/
COPY tools/ ./tools/

# Install the project packages
RUN poetry install --no-interaction --no-ansi

ENV PYTHONUNBUFFERED=1

# Expose standard I/O for MCP communication
ENTRYPOINT ["python", "mcp_server.py"]
