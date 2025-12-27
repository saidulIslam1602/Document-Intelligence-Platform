#!/bin/bash

# Configure OpenAI API Key Securely
# This script updates .env.local with your OpenAI API key

echo "OpenAI API Key Configuration"
echo "============================="
echo ""
echo "This script will configure your OpenAI API key for local development."
echo "The key will be stored in .env.local (which is gitignored)."
echo ""

# Check if .env.local exists
if [ ! -f .env.local ]; then
    echo "Error: .env.local not found. Run ./scripts/local_setup.sh first."
    exit 1
fi

# Prompt for API key
echo "Enter your OpenAI API key (starts with sk-):"
echo "(Press Enter to skip and use mock services)"
read -r api_key

if [ -z "$api_key" ]; then
    echo ""
    echo "No API key provided. Using mock services."
    sed -i 's/USE_MOCK_SERVICES=false/USE_MOCK_SERVICES=true/' .env.local
    sed -i 's/OPENAI_API_KEY=.*/OPENAI_API_KEY=/' .env.local
else
    # Validate key format
    if [[ ! "$api_key" =~ ^sk- ]]; then
        echo ""
        echo "Warning: API key doesn't start with 'sk-'. This may not be valid."
        echo "Continue anyway? (y/N)"
        read -r confirm
        if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
            echo "Configuration cancelled."
            exit 1
        fi
    fi
    
    echo ""
    echo "Configuring OpenAI API key..."
    
    # Update .env.local
    sed -i 's/USE_MOCK_SERVICES=true/USE_MOCK_SERVICES=false/' .env.local
    sed -i "s|OPENAI_API_KEY=.*|OPENAI_API_KEY=$api_key|" .env.local
    
    echo "✓ Configuration complete!"
fi

echo ""
echo "Configuration Summary:"
echo "---------------------"
grep "USE_MOCK_SERVICES" .env.local
grep "OPENAI_API_KEY" .env.local | sed 's/\(OPENAI_API_KEY=sk-[^[:space:]]\{20\}\).*/\1.../'
echo ""
echo "To test the configuration:"
echo "  python3 scripts/test_openai.py"
echo ""
echo "To start services:"
echo "  ./start.sh"
echo ""

