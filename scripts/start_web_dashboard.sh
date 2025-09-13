#!/bin/bash
# Microsoft-Grade Web Dashboard Launcher
# Starts the Document Intelligence Platform with production-ready configuration

echo "🚀 Document Intelligence Platform - Web Dashboard"
echo "================================================"

# Check if we're in the right directory
if [ ! -f "src/web/dashboard.py" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    echo "💡 Current directory: $(pwd)"
    echo "📁 Expected files: src/web/dashboard.py"
    exit 1
fi

# Check Python installation
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.9+"
    exit 1
fi

# Check if virtual environment exists, create if not
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "📦 Installing dependencies..."
pip install -q --upgrade pip
pip install -q fastapi uvicorn python-multipart openai python-dotenv pandas numpy

# Check for OpenAI API key
if [ ! -f "local.env" ]; then
    echo "❌ Error: local.env file not found!"
    echo "💡 Please create local.env with your OpenAI API key:"
    echo "   echo 'OPENAI_API_KEY=your_key_here' > local.env"
    exit 1
fi

# Check if OpenAI API key is set
if ! grep -q "OPENAI_API_KEY=sk-" local.env; then
    echo "❌ Error: OpenAI API key not found in local.env!"
    echo "💡 Please add your OpenAI API key to local.env:"
    echo "   OPENAI_API_KEY=sk-your-key-here"
    exit 1
fi

# Create logs directory
mkdir -p logs

# Start the web dashboard
echo "🌐 Starting Microsoft Fluent UI Web Dashboard..."
echo "📱 Dashboard URL: http://localhost:8000"
echo "📊 API Documentation: http://localhost:8000/api/docs"
echo "🔌 WebSocket: ws://localhost:8000/ws"
echo "=" * 50
echo "Press Ctrl+C to stop the server"
echo "=" * 50

# Start the server
cd src/web
python3 dashboard.py