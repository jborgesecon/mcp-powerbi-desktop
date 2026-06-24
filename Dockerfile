FROM python:3.11-slim

# Setup build and environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_HOME="/opt/poetry"

# Update path to include Poetry
ENV PATH="$POETRY_HOME/bin:$PATH"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Copy dependency files
COPY pyproject.toml README.md ./

# Install python dependencies
RUN poetry install --no-interaction --no-ansi --no-root

# Copy application source code
COPY mcp_server.py ./
COPY powerbi/ ./powerbi/
COPY tools/ ./tools/

# Install the project itself
RUN poetry install --no-interaction --no-ansi

# Create a secure non-root user and assign ownership of /app
RUN groupadd -g 10001 mcpuser && \
    useradd -u 10001 -g mcpuser -m -d /home/mcpuser mcpuser && \
    chown -R mcpuser:mcpuser /app

# Switch to the non-root user
USER mcpuser

# Add a healthcheck to verify core python dependencies are loadable
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import mcp; import psutil" || exit 1

# Stdio is the default communication method for MCP
ENTRYPOINT ["python", "mcp_server.py"]
