#!/bin/bash
# Test runner script for Document Intelligence Platform

echo "🚀 Document Intelligence Platform - Test Runner"
echo "=============================================="

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.9+"
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not installed. Please install pip"
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt

# Run quick test
echo "🧪 Running quick test..."
python3 tests/quick_test.py

# Run demo script
echo "🎭 Running demo script..."
python3 tests/demo_script.py

# Check if Docker is available
if command -v docker &> /dev/null; then
    echo "🐳 Docker is available. Starting services..."
    docker-compose up -d
    
    # Wait for services to start
    echo "⏳ Waiting for services to start..."
    sleep 10
    
    # Run API tests
    echo "🔌 Running API tests..."
    python3 tests/test_api.py
    
    # Stop services
    echo "🛑 Stopping services..."
    docker-compose down
else
    echo "⚠️ Docker not available. Skipping API tests."
    echo "💡 Install Docker to test API endpoints"
fi

echo "✅ Test run complete!"
echo "🎉 Your Document Intelligence Platform is ready!"