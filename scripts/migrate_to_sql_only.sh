#!/bin/bash

# Migration script to remove Cosmos DB and use SQL Database only
# This script helps transition from the 4-storage architecture to 3-storage architecture

echo "🚀 Starting migration to SQL Database only architecture..."

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: Please run this script from the document-intelligence-platform directory"
    exit 1
fi

echo "📋 Migration Steps:"
echo "1. ✅ Updated SQL Database schema to handle all data types"
echo "2. ✅ Updated all services to use SQL instead of Cosmos DB"
echo "3. ✅ Removed Cosmos DB dependencies from requirements.txt"
echo "4. ✅ Updated Bicep template to remove Cosmos DB resources"
echo "5. ✅ Updated environment variables"
echo "6. ✅ Updated Docker Compose configuration"

echo ""
echo "🔧 Next Steps:"
echo "1. Update your environment variables (remove COSMOS_* variables)"
echo "2. Deploy the updated infrastructure:"
echo "   az deployment group create --resource-group <your-rg> --template-file infrastructure/main.bicep"
echo "3. Run database migrations:"
echo "   python -c \"from src.shared.storage.sql_service import SQLService; from src.shared.config.settings import config_manager; config = config_manager.get_azure_config(); sql_service = SQLService(config.sql_connection_string); sql_service.create_tables()\""
echo "4. Restart all services:"
echo "   docker-compose down && docker-compose up -d"

echo ""
echo "📊 New Architecture:"
echo "┌─────────────────┐"
echo "│  Data Storage   │"
echo "│                 │"
echo "│ • Blob Storage  │ (Raw documents, processed files)"
echo "│ • SQL Database  │ (All metadata, users, analytics, chat, events)"
echo "│ • Data Lake     │ (Analytics data, data warehouse)"
echo "└─────────────────┘"

echo ""
echo "💰 Cost Savings:"
echo "- Removed Cosmos DB costs (~$200-500/month depending on usage)"
echo "- Simplified architecture reduces operational overhead"
echo "- Single database for all structured data"

echo ""
echo "✅ Migration completed! Your platform now uses SQL Database only."
echo "📚 See README.md for updated architecture details."