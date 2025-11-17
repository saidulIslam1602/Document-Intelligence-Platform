FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared modules and microservice code
COPY src/shared ./src/shared/
COPY src/microservices/api-gateway ./src/microservices/api-gateway/

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8003

# Run the application
CMD ["python", "-m", "uvicorn", "src.microservices.api-gateway.main:app", "--host", "0.0.0.0", "--port", "8003"]
