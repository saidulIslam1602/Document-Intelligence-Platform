FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (including PostgreSQL client libraries)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    unixodbc-dev \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared modules first
COPY src/__init__.py ./src/
COPY src/shared ./src/shared/
COPY src/microservices/__init__.py ./src/microservices/

# Copy microservice code
COPY src/microservices/api-gateway ./src/microservices/api-gateway/

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8003

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# Run the application from the microservice directory using wrapper script
WORKDIR /app/src/microservices/api-gateway
CMD ["python", "run.py"]
