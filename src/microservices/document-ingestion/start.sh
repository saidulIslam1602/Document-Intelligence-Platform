#!/bin/bash
# Startup script for document-ingestion microservice
cd /app
export PYTHONPATH=/app
exec python -m uvicorn src.microservices.document_ingestion.main:app --host 0.0.0.0 --port 8000

