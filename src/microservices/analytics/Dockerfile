FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    unixodbc-dev \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared modules first
COPY src/__init__.py ./src/
COPY src/shared ./src/shared/
COPY src/microservices/__init__.py ./src/microservices/

# Copy microservice code
COPY src/microservices/analytics ./src/microservices/analytics/

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Run the application from the microservice directory using wrapper script
WORKDIR /app/src/microservices/analytics
CMD ["python", "run.py"]
