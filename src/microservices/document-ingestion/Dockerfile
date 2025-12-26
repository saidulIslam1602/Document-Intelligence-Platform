FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared modules first
COPY src/__init__.py ./src/
COPY src/shared ./src/shared/
COPY src/microservices/__init__.py ./src/microservices/

# Copy microservice code
COPY src/microservices/document-ingestion ./src/microservices/document-ingestion/

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application from the microservice directory using wrapper script
WORKDIR /app/src/microservices/document-ingestion
CMD ["python", "run.py"]
