#!/bin/bash
# Microsoft-Grade Document Intelligence Platform Launcher
# Starts all services with production-ready configuration

echo "🚀 Document Intelligence Platform - Enterprise Launcher"
echo "======================================================"

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

# Function to start service
start_service() {
    local service_name=$1
    local script_path=$2
    local port=$3
    
    echo "🚀 Starting $service_name on port $port..."
    cd "$script_path"
    nohup python3 -m uvicorn $(basename $script_path .py):app --host 0.0.0.0 --port $port --reload > "../../logs/${service_name}.log" 2>&1 &
    echo $! > "../../logs/${service_name}.pid"
    cd - > /dev/null
}

# Function to check if service is running
check_service() {
    local service_name=$1
    local port=$2
    
    sleep 2
    if curl -s "http://localhost:$port/health" > /dev/null 2>&1; then
        echo "✅ $service_name is running on port $port"
        return 0
    else
        echo "❌ $service_name failed to start on port $port"
        return 1
    fi
}

# Start all services
echo "🌐 Starting Web Dashboard..."
start_service "web-dashboard" "src/web" "8000"

echo "📡 Starting API Service..."
start_service "api-service" "src/web" "8001"

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 5

# Check service health
echo "🔍 Checking service health..."
all_healthy=true

if ! check_service "web-dashboard" "8000"; then
    all_healthy=false
fi

if ! check_service "api-service" "8001"; then
    all_healthy=false
fi

# Display results
echo ""
echo "======================================================"
if [ "$all_healthy" = true ]; then
    echo "🎉 Document Intelligence Platform is running!"
    echo ""
    echo "📱 Web Dashboard: http://localhost:8000"
    echo "📡 API Service: http://localhost:8001"
    echo "📚 API Documentation: http://localhost:8001/docs"
    echo "🔌 WebSocket: ws://localhost:8000/ws"
    echo ""
    echo "🎯 Features Available:"
    echo "   ✅ AI-Powered Document Processing"
    echo "   ✅ Real-time Analytics Dashboard"
    echo "   ✅ Microsoft Fluent UI Design"
    echo "   ✅ WebSocket Real-time Updates"
    echo "   ✅ A/B Testing Framework"
    echo "   ✅ Event Sourcing"
    echo "   ✅ Enterprise-grade APIs"
    echo ""
    echo "💡 Upload documents to see AI processing in action!"
    echo "🛑 Press Ctrl+C to stop all services"
    echo "======================================================"
    
    # Keep script running and show logs
    echo "📋 Service logs (Ctrl+C to stop):"
    echo "======================================================"
    tail -f logs/*.log
else
    echo "❌ Some services failed to start"
    echo "📋 Check logs for details:"
    echo "   - Web Dashboard: logs/web-dashboard.log"
    echo "   - API Service: logs/api-service.log"
    exit 1
fi