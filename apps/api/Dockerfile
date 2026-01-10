# FastAPI Backend Dockerfile
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install build tools
RUN pip install --upgrade pip setuptools wheel hatchling

# Copy pyproject.toml first for caching
COPY pyproject.toml ./
COPY README.md ./

# Copy application code
COPY app ./app

# Copy alembic for migrations
COPY alembic ./alembic
COPY alembic.ini ./

# Copy startup scripts
COPY start.sh ./
COPY start-worker.sh ./
RUN chmod +x start.sh start-worker.sh

# Install the package
RUN pip install .

# Expose port
EXPOSE 8000

# Default command - run migrations then start API
CMD ["./start.sh"]
