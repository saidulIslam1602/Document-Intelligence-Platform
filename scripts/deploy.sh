#!/bin/bash

# Azure Infrastructure Deployment Script
# Deploys the complete Document Intelligence Platform infrastructure

set -e

# Configuration
RESOURCE_GROUP_NAME="document-intelligence-rg"
LOCATION="East US"
ENVIRONMENT="dev"
APP_NAME_PREFIX="docintel"
DEPLOYMENT_NAME="docintel-deployment-$(date +%Y%m%d-%H%M%S)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if Azure CLI is installed
    if ! command -v az &> /dev/null; then
        log_error "Azure CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check if user is logged in
    if ! az account show &> /dev/null; then
        log_error "Not logged in to Azure CLI. Please run 'az login' first."
        exit 1
    fi
    
    # Check if Bicep is installed
    if ! command -v az bicep version &> /dev/null; then
        log_warning "Bicep not found. Installing..."
        az bicep install
    fi
    
    log_success "Prerequisites check completed"
}

# Create resource group
create_resource_group() {
    log_info "Creating resource group: $RESOURCE_GROUP_NAME"
    
    if az group show --name $RESOURCE_GROUP_NAME &> /dev/null; then
        log_warning "Resource group $RESOURCE_GROUP_NAME already exists"
    else
        az group create \
            --name $RESOURCE_GROUP_NAME \
            --location "$LOCATION" \
            --tags Environment=$ENVIRONMENT Application="Document Intelligence Platform"
        log_success "Resource group created"
    fi
}

# Deploy infrastructure
deploy_infrastructure() {
    log_info "Deploying infrastructure with Bicep..."
    
    az deployment group create \
        --resource-group $RESOURCE_GROUP_NAME \
        --name $DEPLOYMENT_NAME \
        --template-file infrastructure/main.bicep \
        --parameters \
            environment=$ENVIRONMENT \
            appNamePrefix=$APP_NAME_PREFIX \
            location="$LOCATION" \
            enablePublicAccess=true \
        --verbose
    
    log_success "Infrastructure deployment completed"
}

# Get deployment outputs
get_deployment_outputs() {
    log_info "Retrieving deployment outputs..."
    
    OUTPUTS=$(az deployment group show \
        --resource-group $RESOURCE_GROUP_NAME \
        --name $DEPLOYMENT_NAME \
        --query properties.outputs \
        --output json)
    
    # Extract key values
    STORAGE_ACCOUNT_NAME=$(echo $OUTPUTS | jq -r '.storageAccountName.value')
    COSMOS_ENDPOINT=$(echo $OUTPUTS | jq -r '.cosmosAccountEndpoint.value')
    EVENT_HUB_CONNECTION_STRING=$(echo $OUTPUTS | jq -r '.eventHubConnectionString.value')
    API_GATEWAY_URL=$(echo $OUTPUTS | jq -r '.apiGatewayUrl.value')
    
    log_success "Deployment outputs retrieved"
}

# Create environment file
create_environment_file() {
    log_info "Creating environment configuration file..."
    
    cat > .env << EOF
# Azure Configuration
AZURE_SUBSCRIPTION_ID=$(az account show --query id -o tsv)
AZURE_RESOURCE_GROUP=$RESOURCE_GROUP_NAME
AZURE_LOCATION="$LOCATION"
AZURE_TENANT_ID=$(az account show --query tenantId -o tsv)

# Storage Configuration
STORAGE_ACCOUNT_NAME=$STORAGE_ACCOUNT_NAME
STORAGE_CONNECTION_STRING=$(az storage account show-connection-string --name $STORAGE_ACCOUNT_NAME --resource-group $RESOURCE_GROUP_NAME --query connectionString -o tsv)

# Cosmos DB Configuration
COSMOS_ENDPOINT=$COSMOS_ENDPOINT
COSMOS_KEY=$(az cosmosdb keys list --name ${APP_NAME_PREFIX}-${ENVIRONMENT}-cosmos --resource-group $RESOURCE_GROUP_NAME --query primaryMasterKey -o tsv)
COSMOS_DATABASE=documentdb

# Event Hub Configuration
EVENT_HUB_CONNECTION_STRING=$EVENT_HUB_CONNECTION_STRING

# Service Bus Configuration
SERVICE_BUS_CONNECTION_STRING=$(az servicebus namespace authorization-rule keys list --name RootManageSharedAccessKey --namespace-name ${APP_NAME_PREFIX}-${ENVIRONMENT}-servicebus --resource-group $RESOURCE_GROUP_NAME --query primaryConnectionString -o tsv)

# AI Services Configuration
FORM_RECOGNIZER_ENDPOINT=$(echo $OUTPUTS | jq -r '.formRecognizerEndpoint.value')
FORM_RECOGNIZER_KEY=$(echo $OUTPUTS | jq -r '.formRecognizerKey.value')
OPENAI_ENDPOINT=$(echo $OUTPUTS | jq -r '.openaiEndpoint.value')
OPENAI_API_KEY=$(echo $OUTPUTS | jq -r '.openaiKey.value')
OPENAI_DEPLOYMENT=gpt-4

# Cognitive Search Configuration
COGNITIVE_SEARCH_ENDPOINT=$(echo $OUTPUTS | jq -r '.searchEndpoint.value')
COGNITIVE_SEARCH_KEY=$(echo $OUTPUTS | jq -r '.searchKey.value')

# Application Insights Configuration
APPLICATION_INSIGHTS_CONNECTION_STRING=$(echo $OUTPUTS | jq -r '.applicationInsightsConnectionString.value')

# Key Vault Configuration
KEY_VAULT_URL=$(echo $OUTPUTS | jq -r '.keyVaultUri.value')

# Redis Configuration
REDIS_HOSTNAME=$(echo $OUTPUTS | jq -r '.redisHostName.value')
REDIS_CONNECTION_STRING=redis://$(echo $OUTPUTS | jq -r '.redisHostName.value'):6380,ssl=true

# Container Registry Configuration
CONTAINER_REGISTRY_LOGIN_SERVER=$(echo $OUTPUTS | jq -r '.containerRegistryLoginServer.value')

# API Gateway Configuration
API_GATEWAY_URL=$API_GATEWAY_URL

# Environment
ENVIRONMENT=$ENVIRONMENT
JWT_SECRET_KEY=your-jwt-secret-key-change-in-production
CLIENT_ID=your-client-id
CLIENT_SECRET=your-client-secret
EOF
    
    log_success "Environment file created: .env"
}

# Build and push container images
build_and_push_images() {
    log_info "Building and pushing container images..."
    
    # Login to container registry
    az acr login --name ${APP_NAME_PREFIX}acr
    
    # Build and push each microservice
    SERVICES=("document-ingestion" "ai-processing" "analytics" "api-gateway")
    
    for service in "${SERVICES[@]}"; do
        log_info "Building $service image..."
        
        # Build image
        docker build -t ${APP_NAME_PREFIX}acr.azurecr.io/$service:latest \
            -f src/microservices/$service/Dockerfile \
            src/microservices/$service/
        
        # Push image
        docker push ${APP_NAME_PREFIX}acr.azurecr.io/$service:latest
        
        log_success "$service image built and pushed"
    done
}

# Deploy container apps
deploy_container_apps() {
    log_info "Deploying container apps..."
    
    # Update container apps with new images
    az containerapp update \
        --name ${APP_NAME_PREFIX}-${ENVIRONMENT}-document-ingestion \
        --resource-group $RESOURCE_GROUP_NAME \
        --image ${APP_NAME_PREFIX}acr.azurecr.io/document-ingestion:latest
    
    az containerapp update \
        --name ${APP_NAME_PREFIX}-${ENVIRONMENT}-ai-processing \
        --resource-group $RESOURCE_GROUP_NAME \
        --image ${APP_NAME_PREFIX}acr.azurecr.io/ai-processing:latest
    
    az containerapp update \
        --name ${APP_NAME_PREFIX}-${ENVIRONMENT}-analytics \
        --resource-group $RESOURCE_GROUP_NAME \
        --image ${APP_NAME_PREFIX}acr.azurecr.io/analytics:latest
    
    az containerapp update \
        --name ${APP_NAME_PREFIX}-${ENVIRONMENT}-api-gateway \
        --resource-group $RESOURCE_GROUP_NAME \
        --image ${APP_NAME_PREFIX}acr.azurecr.io/api-gateway:latest
    
    log_success "Container apps deployed"
}

# Run health checks
run_health_checks() {
    log_info "Running health checks..."
    
    # Wait for services to be ready
    sleep 30
    
    # Check API Gateway
    if curl -f -s "$API_GATEWAY_URL/health" > /dev/null; then
        log_success "API Gateway is healthy"
    else
        log_warning "API Gateway health check failed"
    fi
    
    # Check individual services
    SERVICES=("document-ingestion" "ai-processing" "analytics")
    
    for service in "${SERVICES[@]}"; do
        SERVICE_URL="https://${APP_NAME_PREFIX}-${ENVIRONMENT}-${service}.${APP_NAME_PREFIX}-${ENVIRONMENT}-container-env.${LOCATION,,}.azurecontainerapps.io/health"
        
        if curl -f -s "$SERVICE_URL" > /dev/null; then
            log_success "$service is healthy"
        else
            log_warning "$service health check failed"
        fi
    done
}

# Display deployment summary
display_summary() {
    log_info "Deployment Summary"
    echo "=================="
    echo "Resource Group: $RESOURCE_GROUP_NAME"
    echo "Location: $LOCATION"
    echo "Environment: $ENVIRONMENT"
    echo "API Gateway URL: $API_GATEWAY_URL"
    echo "Container Registry: ${APP_NAME_PREFIX}acr.azurecr.io"
    echo ""
    echo "Next Steps:"
    echo "1. Update the .env file with your specific configuration"
    echo "2. Configure Azure OpenAI deployments"
    echo "3. Set up monitoring and alerting"
    echo "4. Test the API endpoints"
    echo ""
    echo "API Documentation: $API_GATEWAY_URL/docs"
    echo "Analytics Dashboard: $API_GATEWAY_URL/analytics/dashboard"
}

# Main deployment function
main() {
    log_info "Starting Document Intelligence Platform deployment..."
    
    check_prerequisites
    create_resource_group
    deploy_infrastructure
    get_deployment_outputs
    create_environment_file
    build_and_push_images
    deploy_container_apps
    run_health_checks
    display_summary
    
    log_success "Deployment completed successfully!"
}

# Run main function
main "$@"