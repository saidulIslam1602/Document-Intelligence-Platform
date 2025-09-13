#!/bin/bash

# Deploy Document Intelligence Platform with SQL Database and Data Lake
# This script deploys the complete infrastructure including all four storage types

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
RESOURCE_GROUP="document-intelligence-rg"
LOCATION="East US"
ENVIRONMENT="dev"
APP_NAME_PREFIX="docintel"

echo -e "${BLUE}🚀 Deploying Document Intelligence Platform with SQL Database and Data Lake${NC}"
echo -e "${YELLOW}Resource Group: ${RESOURCE_GROUP}${NC}"
echo -e "${YELLOW}Location: ${LOCATION}${NC}"
echo -e "${YELLOW}Environment: ${ENVIRONMENT}${NC}"

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo -e "${RED}❌ Azure CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if user is logged in
if ! az account show &> /dev/null; then
    echo -e "${RED}❌ Not logged in to Azure. Please run 'az login' first.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Azure CLI is ready${NC}"

# Create resource group if it doesn't exist
echo -e "${BLUE}📦 Creating resource group...${NC}"
az group create \
    --name $RESOURCE_GROUP \
    --location "$LOCATION" \
    --output table

# Deploy infrastructure
echo -e "${BLUE}🏗️ Deploying infrastructure with Bicep...${NC}"
az deployment group create \
    --resource-group $RESOURCE_GROUP \
    --template-file infrastructure/main.bicep \
    --parameters \
        environment=$ENVIRONMENT \
        appNamePrefix=$APP_NAME_PREFIX \
        enablePublicAccess=true \
    --output table

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Infrastructure deployed successfully${NC}"
else
    echo -e "${RED}❌ Infrastructure deployment failed${NC}"
    exit 1
fi

# Get deployment outputs
echo -e "${BLUE}📋 Getting deployment outputs...${NC}"
OUTPUTS=$(az deployment group show \
    --resource-group $RESOURCE_GROUP \
    --name main \
    --query properties.outputs \
    --output json)

# Extract key values
STORAGE_ACCOUNT_NAME=$(echo $OUTPUTS | jq -r '.storageAccountName.value')
DATA_LAKE_ACCOUNT_NAME=$(echo $OUTPUTS | jq -r '.dataLakeStorageAccountName.value')
COSMOS_ENDPOINT=$(echo $OUTPUTS | jq -r '.cosmosAccountEndpoint.value')
SQL_SERVER_NAME=$(echo $OUTPUTS | jq -r '.sqlServerName.value')
SQL_DATABASE_NAME=$(echo $OUTPUTS | jq -r '.sqlDatabaseName.value')

echo -e "${GREEN}✅ Deployment outputs retrieved${NC}"

# Create environment file
echo -e "${BLUE}📝 Creating environment configuration...${NC}"
cat > .env << EOF
# Azure Configuration
AZURE_SUBSCRIPTION_ID=$(az account show --query id -o tsv)
AZURE_RESOURCE_GROUP=$RESOURCE_GROUP
AZURE_LOCATION="$LOCATION"
AZURE_TENANT_ID=$(az account show --query tenantId -o tsv)

# Storage Account
STORAGE_ACCOUNT_NAME=$STORAGE_ACCOUNT_NAME
STORAGE_CONNECTION_STRING=$(az storage account show-connection-string --name $STORAGE_ACCOUNT_NAME --resource-group $RESOURCE_GROUP --query connectionString -o tsv)
STORAGE_ACCOUNT_KEY=$(az storage account keys list --name $STORAGE_ACCOUNT_NAME --resource-group $RESOURCE_GROUP --query '[0].value' -o tsv)

# Data Lake Storage
DATA_LAKE_STORAGE_ACCOUNT_NAME=$DATA_LAKE_ACCOUNT_NAME
DATA_LAKE_CONNECTION_STRING=$(az storage account show-connection-string --name $DATA_LAKE_ACCOUNT_NAME --resource-group $RESOURCE_GROUP --query connectionString -o tsv)
DATA_LAKE_ACCOUNT_KEY=$(az storage account keys list --name $DATA_LAKE_ACCOUNT_NAME --resource-group $RESOURCE_GROUP --query '[0].value' -o tsv)

# Cosmos DB
COSMOS_ENDPOINT=$COSMOS_ENDPOINT
COSMOS_KEY=$(az cosmosdb keys list --name ${APP_NAME_PREFIX}-${ENVIRONMENT}-cosmos --resource-group $RESOURCE_GROUP --query primaryMasterKey -o tsv)
COSMOS_DATABASE=documentdb

# SQL Database
SQL_CONNECTION_STRING=Server=tcp:${SQL_SERVER_NAME}.database.windows.net,1433;Initial Catalog=${SQL_DATABASE_NAME};Persist Security Info=False;User ID=sqladmin;Password=TempPassword123!;MultipleActiveResultSets=False;Encrypt=True;TrustServerCertificate=False;Connection Timeout=30;
SQL_SERVER_NAME=$SQL_SERVER_NAME
SQL_DATABASE_NAME=$SQL_DATABASE_NAME

# Event Hubs
EVENT_HUB_CONNECTION_STRING=$(az eventhubs namespace authorization-rule keys list --resource-group $RESOURCE_GROUP --namespace-name ${APP_NAME_PREFIX}-${ENVIRONMENT}-eventhub --name RootManageSharedAccessKey --query primaryConnectionString -o tsv)
SERVICE_BUS_CONNECTION_STRING=$(az servicebus namespace authorization-rule keys list --resource-group $RESOURCE_GROUP --namespace-name ${APP_NAME_PREFIX}-${ENVIRONMENT}-servicebus --name RootManageSharedAccessKey --query primaryConnectionString -o tsv)

# AI Services (you'll need to configure these separately)
FORM_RECOGNIZER_ENDPOINT=
FORM_RECOGNIZER_KEY=
OPENAI_ENDPOINT=
OPENAI_API_KEY=
OPENAI_DEPLOYMENT=gpt-4
COGNITIVE_SEARCH_ENDPOINT=
COGNITIVE_SEARCH_KEY=

# Security
KEY_VAULT_URL=$(az keyvault show --name ${APP_NAME_PREFIX}-${ENVIRONMENT}-kv --resource-group $RESOURCE_GROUP --query properties.vaultUri -o tsv)
CLIENT_ID=
CLIENT_SECRET=

# Monitoring
APPLICATION_INSIGHTS_CONNECTION_STRING=$(az monitor app-insights component show --app ${APP_NAME_PREFIX}-${ENVIRONMENT}-appinsights --resource-group $RESOURCE_GROUP --query connectionString -o tsv)
LOG_ANALYTICS_WORKSPACE_ID=$(az monitor log-analytics workspace show --workspace-name ${APP_NAME_PREFIX}-${ENVIRONMENT}-logs --resource-group $RESOURCE_GROUP --query customerId -o tsv)

# Redis
REDIS_URL=redis://${APP_NAME_PREFIX}-${ENVIRONMENT}-redis.redis.cache.windows.net:6380

# Application Settings
ENVIRONMENT=$ENVIRONMENT
LOG_LEVEL=INFO
API_VERSION=v1
EOF

echo -e "${GREEN}✅ Environment file created: .env${NC}"

# Install Python dependencies
echo -e "${BLUE}📦 Installing Python dependencies...${NC}"
pip install -r requirements.txt

# Initialize SQL Database tables
echo -e "${BLUE}🗄️ Initializing SQL Database tables...${NC}"
python3 -c "
from src.shared.storage.sql_service import SQLService
import os
from dotenv import load_dotenv

load_dotenv()
sql_service = SQLService(os.getenv('SQL_CONNECTION_STRING'))
sql_service.create_tables()
print('✅ Database tables initialized')
"

echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
echo -e "${YELLOW}📋 Next steps:${NC}"
echo -e "1. Configure AI services (OpenAI, Form Recognizer, Cognitive Search) in the .env file"
echo -e "2. Update security settings (CLIENT_ID, CLIENT_SECRET) in the .env file"
echo -e "3. Run the application: docker-compose up -d"
echo -e "4. Access the API Gateway at the URL shown in the deployment outputs"

echo -e "${BLUE}📊 Storage Summary:${NC}"
echo -e "• Blob Storage: $STORAGE_ACCOUNT_NAME (documents, checkpoints)"
echo -e "• Data Lake: $DATA_LAKE_ACCOUNT_NAME (raw-data, processed-data, analytics-data, data-warehouse)"
echo -e "• Cosmos DB: ${APP_NAME_PREFIX}-${ENVIRONMENT}-cosmos (documents, analytics, events)"
echo -e "• SQL Database: $SQL_SERVER_NAME/$SQL_DATABASE_NAME (users, jobs, metrics)"
echo -e "• Redis Cache: ${APP_NAME_PREFIX}-${ENVIRONMENT}-redis (caching, sessions)"