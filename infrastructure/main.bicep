// Azure Bicep template for Document Intelligence Platform
// Enterprise-grade infrastructure deployment

@description('The name of the resource group')
param resourceGroupName string = 'document-intelligence-rg'

@description('The location for all resources')
param location string = resourceGroup().location

@description('Environment name (dev, staging, prod)')
@allowed(['dev', 'staging', 'prod'])
param environment string = 'dev'

@description('Application name prefix')
param appNamePrefix string = 'docintel'

@description('Azure OpenAI deployment name')
param openaiDeploymentName string = 'gpt-4'

@description('Enable public access for development')
param enablePublicAccess bool = false

// Variables
var resourcePrefix = '${appNamePrefix}-${environment}'
var tags = {
  Environment: environment
  Application: 'Document Intelligence Platform'
  ManagedBy: 'Bicep'
  CostCenter: 'Engineering'
}

// =============================================
// STORAGE ACCOUNT
// =============================================
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: '${resourcePrefix}storage${uniqueString(resourceGroup().id)}'
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    networkAcls: {
      defaultAction: enablePublicAccess ? 'Allow' : 'Deny'
    }
  }
}

// Blob containers
resource documentsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: storageAccount::blobServices
  name: 'documents'
  properties: {
    publicAccess: 'None'
  }
}

resource checkpointsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: storageAccount::blobServices
  name: 'checkpoints'
  properties: {
    publicAccess: 'None'
  }
}


// =============================================
// AZURE SQL DATABASE
// =============================================
resource sqlServer 'Microsoft.Sql/servers@2023-05-01-preview' = {
  name: '${resourcePrefix}-sqlserver'
  location: location
  tags: tags
  properties: {
    administratorLogin: 'sqladmin'
    administratorLoginPassword: 'TempPassword123!'
    version: '12.0'
    minimalTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'
  }
}

resource sqlDatabase 'Microsoft.Sql/servers/databases@2023-05-01-preview' = {
  parent: sqlServer
  name: 'documentintelligence'
  location: location
  tags: tags
  sku: {
    name: environment == 'dev' ? 'Basic' : 'S2'
    tier: environment == 'dev' ? 'Basic' : 'Standard'
  }
  properties: {
    collation: 'SQL_Latin1_General_CP1_CI_AS'
    maxSizeBytes: environment == 'dev' ? 2147483648 : 107374182400 // 2GB for dev, 100GB for prod
    requestedServiceObjectiveName: environment == 'dev' ? 'Basic' : 'S2'
  }
}

// SQL Server Firewall Rule
resource sqlFirewallRule 'Microsoft.Sql/servers/firewallRules@2023-05-01-preview' = {
  parent: sqlServer
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

// =============================================
// AZURE DATA LAKE STORAGE GEN2
// =============================================
resource dataLakeStorageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: '${resourcePrefix}datalake${uniqueString(resourceGroup().id)}'
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    isHnsEnabled: true // Enable hierarchical namespace for Data Lake
    networkAcls: {
      defaultAction: enablePublicAccess ? 'Allow' : 'Deny'
    }
  }
}

// Data Lake containers
resource rawDataContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: dataLakeStorageAccount::blobServices
  name: 'raw-data'
  properties: {
    publicAccess: 'None'
    metadata: {
      purpose: 'Raw data ingestion'
    }
  }
}

resource processedDataContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: dataLakeStorageAccount::blobServices
  name: 'processed-data'
  properties: {
    publicAccess: 'None'
    metadata: {
      purpose: 'Processed and transformed data'
    }
  }
}

resource analyticsDataContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: dataLakeStorageAccount::blobServices
  name: 'analytics-data'
  properties: {
    publicAccess: 'None'
    metadata: {
      purpose: 'Analytics and ML training data'
    }
  }
}

resource dataWarehouseContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: dataLakeStorageAccount::blobServices
  name: 'data-warehouse'
  properties: {
    publicAccess: 'None'
    metadata: {
      purpose: 'Data warehouse storage'
    }
  }
}

// =============================================
// EVENT HUBS
// =============================================
resource eventHubNamespace 'Microsoft.EventHub/namespaces@2023-01-01-preview' = {
  name: '${resourcePrefix}-eventhub'
  location: location
  tags: tags
  sku: {
    name: 'Standard'
    tier: 'Standard'
    capacity: 1
  }
  properties: {
    minimumTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: false
    zoneRedundant: false
  }
}

resource documentProcessingEventHub 'Microsoft.EventHub/namespaces/eventhubs@2023-01-01-preview' = {
  parent: eventHubNamespace
  name: 'document-processing'
  properties: {
    messageRetentionInDays: 7
    partitionCount: 4
    status: 'Active'
  }
}

// =============================================
// SERVICE BUS
// =============================================
resource serviceBusNamespace 'Microsoft.ServiceBus/namespaces@2022-10-01-preview' = {
  name: '${resourcePrefix}-servicebus'
  location: location
  tags: tags
  sku: {
    name: 'Standard'
    tier: 'Standard'
  }
  properties: {
    minimumTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: false
  }
}

resource documentProcessingQueue 'Microsoft.ServiceBus/namespaces/queues@2022-10-01-preview' = {
  parent: serviceBusNamespace
  name: 'document-processing'
  properties: {
    maxSizeInMegabytes: 1024
    defaultMessageTimeToLive: 'P14D'
    lockDuration: 'PT5M'
    enableDeadLetteringOnMessageExpiration: true
    enableBatchedOperations: true
  }
}

resource batchProcessingQueue 'Microsoft.ServiceBus/namespaces/queues@2022-10-01-preview' = {
  parent: serviceBusNamespace
  name: 'batch-processing'
  properties: {
    maxSizeInMegabytes: 1024
    defaultMessageTimeToLive: 'P14D'
    lockDuration: 'PT5M'
    enableDeadLetteringOnMessageExpiration: true
    enableBatchedOperations: true
  }
}

// =============================================
// AZURE API MANAGEMENT
// =============================================
resource apiManagement 'Microsoft.ApiManagement/service@2023-05-01-preview' = {
  name: '${resourcePrefix}-apim'
  location: location
  tags: tags
  sku: {
    name: environment == 'dev' ? 'Developer' : 'Standard'
    capacity: environment == 'dev' ? 1 : 2
  }
  properties: {
    publisherName: 'Document Intelligence Platform'
    publisherEmail: 'admin@documentintelligence.com'
    notificationSenderEmail: 'noreply@documentintelligence.com'
    publicNetworkAccess: 'Enabled'
    virtualNetworkType: 'None'
    disableGateway: false
    enableClientCertificate: false
    natGatewayState: 'Disabled'
    publicIpAddressId: null
    restore: false
    apiVersionConstraint: null
    minApiVersion: null
    additionalLocations: []
    customProperties: {
      'Microsoft.WindowsAzure.ApiManagement.Gateway.Security.Protocols.Tls10': 'false'
      'Microsoft.WindowsAzure.ApiManagement.Gateway.Security.Protocols.Tls11': 'false'
      'Microsoft.WindowsAzure.ApiManagement.Gateway.Security.Protocols.Ssl30': 'false'
      'Microsoft.WindowsAzure.ApiManagement.Gateway.Security.Ciphers.TripleDes168': 'false'
      'Microsoft.WindowsAzure.ApiManagement.Gateway.Security.Backend.Protocols.Tls10': 'false'
      'Microsoft.WindowsAzure.ApiManagement.Gateway.Security.Backend.Protocols.Tls11': 'false'
      'Microsoft.WindowsAzure.ApiManagement.Gateway.Security.Backend.Protocols.Ssl30': 'false'
    }
  }
}

// API Management API
resource documentIntelligenceAPI 'Microsoft.ApiManagement/service/apis@2023-05-01-preview' = {
  parent: apiManagement
  name: 'document-intelligence-api'
  properties: {
    displayName: 'Document Intelligence API'
    description: 'API for Document Intelligence Platform'
    serviceUrl: 'https://${apiGatewayApp.properties.configuration.ingress.fqdn}'
    path: 'api'
    protocols: ['https']
    subscriptionRequired: true
    apiVersion: 'v1'
    apiVersionSetId: '${apiManagement.id}/apiVersionSets/document-intelligence-versions'
  }
}

// API Version Set
resource apiVersionSet 'Microsoft.ApiManagement/service/apiVersionSets@2023-05-01-preview' = {
  parent: apiManagement
  name: 'document-intelligence-versions'
  properties: {
    displayName: 'Document Intelligence API Versions'
    versioningScheme: 'Segment'
    description: 'Version set for Document Intelligence API'
  }
}

// API Management Operations
resource documentUploadOperation 'Microsoft.ApiManagement/service/apis/operations@2023-05-01-preview' = {
  parent: documentIntelligenceAPI
  name: 'upload-document'
  properties: {
    displayName: 'Upload Document'
    method: 'POST'
    urlTemplate: '/documents/upload'
    description: 'Upload a document for processing'
    templateParameters: []
    request: {
      description: 'Document upload request'
      queryParameters: []
      headers: []
      representations: [
        {
          contentType: 'multipart/form-data'
          schemaId: 'document-upload-schema'
          typeName: 'DocumentUpload'
        }
      ]
    }
    responses: [
      {
        statusCode: 200
        description: 'Document uploaded successfully'
        representations: [
          {
            contentType: 'application/json'
            schemaId: 'document-upload-response-schema'
            typeName: 'DocumentUploadResponse'
          }
        ]
      }
      {
        statusCode: 400
        description: 'Bad request'
        representations: [
          {
            contentType: 'application/json'
            schemaId: 'error-schema'
            typeName: 'ErrorResponse'
          }
        ]
      }
    ]
  }
}

// API Management Policy
resource apiPolicy 'Microsoft.ApiManagement/service/apis/policies@2023-05-01-preview' = {
  parent: documentIntelligenceAPI
  name: 'policy'
  properties: {
    value: '''
    <policies>
        <inbound>
            <!-- Rate limiting -->
            <rate-limit calls="100" renewal-period="60" />
            
            <!-- CORS -->
            <cors allow-credentials="true">
                <allowed-origins>
                    <origin>*</origin>
                </allowed-origins>
                <allowed-methods>
                    <method>GET</method>
                    <method>POST</method>
                    <method>PUT</method>
                    <method>DELETE</method>
                    <method>OPTIONS</method>
                </allowed-methods>
                <allowed-headers>
                    <header>*</header>
                </allowed-headers>
            </cors>
            
            <!-- Authentication -->
            <validate-jwt header-name="Authorization" failed-validation-httpcode="401" failed-validation-error-message="Unauthorized">
                <openid-config url="https://login.microsoftonline.com/${config.tenant_id}/.well-known/openid_configuration" />
                <audiences>
                    <audience>api://document-intelligence</audience>
                </audiences>
                <issuers>
                    <issuer>https://login.microsoftonline.com/${config.tenant_id}/v2.0</issuer>
                </issuers>
            </validate-jwt>
            
            <!-- Request transformation -->
            <set-backend-service base-url="https://${apiGatewayApp.properties.configuration.ingress.fqdn}" />
            
            <!-- Logging -->
            <log-to-eventhub logger-id="document-intelligence-logger">
                @{
                    var request = context.Request;
                    var response = context.Response;
                    return new JObject(
                        new JProperty("timestamp", DateTime.UtcNow),
                        new JProperty("requestId", context.RequestId),
                        new JProperty("method", request.Method),
                        new JProperty("url", request.Url.ToString()),
                        new JProperty("statusCode", response.StatusCode),
                        new JProperty("userId", context.User?.Identity?.Name ?? "anonymous")
                    ).ToString();
                }
            </log-to-eventhub>
        </inbound>
        <backend>
            <forward-request />
        </backend>
        <outbound>
            <!-- Response transformation -->
            <set-header name="X-API-Version" exists-action="override">
                <value>v1</value>
            </set-header>
            
            <!-- Caching for GET requests -->
            <cache-lookup vary-by-developer="false" vary-by-developer-groups="false" />
            <cache-store duration="300" />
        </outbound>
        <on-error>
            <set-status code="500" reason="Internal Server Error" />
            <set-header name="Content-Type" exists-action="override">
                <value>application/json</value>
            </set-header>
            <set-body>
                {
                    "error": "Internal Server Error",
                    "message": "An unexpected error occurred",
                    "requestId": "@{context.RequestId}"
                }
            </set-body>
        </on-error>
    </policies>
    '''
  }
}

// API Management Logger
resource eventHubLogger 'Microsoft.ApiManagement/service/loggers@2023-05-01-preview' = {
  parent: apiManagement
  name: 'document-intelligence-logger'
  properties: {
    loggerType: 'azureEventHub'
    description: 'Event Hub logger for API Management'
    credentials: {
      name: '${eventHubNamespace.name}'
      connectionString: eventHubNamespace.listKeys().primaryConnectionString
    }
  }
}

// API Management Product
resource apiProduct 'Microsoft.ApiManagement/service/products@2023-05-01-preview' = {
  parent: apiManagement
  name: 'document-intelligence-product'
  properties: {
    displayName: 'Document Intelligence Platform'
    description: 'Access to Document Intelligence Platform APIs'
    terms: 'By using this API, you agree to the terms of service.'
    subscriptionRequired: true
    approvalRequired: false
    subscriptionsLimit: 10
    state: 'published'
  }
}

// Add API to Product
resource apiProductApi 'Microsoft.ApiManagement/service/products/apis@2023-05-01-preview' = {
  parent: apiProduct
  name: 'document-intelligence-api'
}

// API Management Subscription
resource apiSubscription 'Microsoft.ApiManagement/service/subscriptions@2023-05-01-preview' = {
  parent: apiManagement
  name: 'document-intelligence-subscription'
  properties: {
    displayName: 'Document Intelligence Subscription'
    scope: '${apiProduct.id}'
    state: 'active'
  }
}

// =============================================
// COGNITIVE SERVICES
// =============================================
resource formRecognizerAccount 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: '${resourcePrefix}-formrecognizer'
  location: location
  tags: tags
  sku: {
    name: 'S0'
  }
  kind: 'FormRecognizer'
  properties: {
    customSubDomainName: '${resourcePrefix}-formrecognizer'
    publicNetworkAccess: 'Enabled'
  }
}

resource openaiAccount 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: '${resourcePrefix}-openai'
  location: location
  tags: tags
  sku: {
    name: 'S0'
  }
  kind: 'OpenAI'
  properties: {
    customSubDomainName: '${resourcePrefix}-openai'
    publicNetworkAccess: 'Enabled'
  }
}

// =============================================
// COGNITIVE SEARCH
// =============================================
resource searchService 'Microsoft.Search/searchServices@2023-11-01' = {
  name: '${resourcePrefix}-search'
  location: location
  tags: tags
  sku: {
    name: environment == 'dev' ? 'Free' : 'Standard'
  }
  properties: {
    replicaCount: environment == 'dev' ? 1 : 3
    partitionCount: environment == 'dev' ? 1 : 2
    hostingMode: 'Default'
    publicNetworkAccess: 'Enabled'
  }
}

// =============================================
// CONTAINER APPS ENVIRONMENT
// =============================================
resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: '${resourcePrefix}-container-env'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsWorkspace.properties.customerId
        sharedKey: logAnalyticsWorkspace.listKeys().primarySharedKey
      }
    }
    vnetConfiguration: {
      infrastructureSubnetId: vnetSubnet.id
      internal: false
    }
  }
}

// =============================================
// CONTAINER APPS
// =============================================
resource documentIngestionApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: '${resourcePrefix}-document-ingestion'
  location: location
  tags: tags
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        allowInsecure: false
        traffic: [
          {
            weight: 100
            latestRevision: true
          }
        ]
      }
      registries: [
        {
          server: '${resourcePrefix}acr.azurecr.io'
          username: '${resourcePrefix}acr'
          passwordSecretRef: 'acr-password'
        }
      ]
      secrets: [
        {
          name: 'acr-password'
          value: containerRegistry.listCredentials().passwords[0].value
        }
        {
          name: 'cosmos-connection-string'
          value: 'AccountEndpoint=${cosmosAccount.properties.documentEndpoint};AccountKey=${cosmosAccount.listKeys().primaryMasterKey};'
        }
        {
          name: 'storage-connection-string'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${storageAccount.listKeys().keys[0].value};EndpointSuffix=${environment().suffixes.storage}'
        }
        {
          name: 'event-hub-connection-string'
          value: eventHubNamespace.listKeys().primaryConnectionString
        }
        {
          name: 'service-bus-connection-string'
          value: serviceBusNamespace.listKeys().primaryConnectionString
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'document-ingestion'
          image: '${resourcePrefix}acr.azurecr.io/document-ingestion:latest'
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            {
              name: 'AZURE_SUBSCRIPTION_ID'
              value: subscription().subscriptionId
            }
            {
              name: 'AZURE_RESOURCE_GROUP'
              value: resourceGroup().name
            }
            {
              name: 'AZURE_LOCATION'
              value: location
            }
            {
              name: 'STORAGE_CONNECTION_STRING'
              secretRef: 'storage-connection-string'
            }
            {
              name: 'COSMOS_CONNECTION_STRING'
              secretRef: 'cosmos-connection-string'
            }
            {
              name: 'EVENT_HUB_CONNECTION_STRING'
              secretRef: 'event-hub-connection-string'
            }
            {
              name: 'SERVICE_BUS_CONNECTION_STRING'
              secretRef: 'service-bus-connection-string'
            }
          ]
        }
      ]
      scale: {
        minReplicas: environment == 'dev' ? 1 : 2
        maxReplicas: environment == 'dev' ? 3 : 10
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '30'
              }
            }
          }
        ]
      }
    }
  }
}

resource aiProcessingApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: '${resourcePrefix}-ai-processing'
  location: location
  tags: tags
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8001
        allowInsecure: false
        traffic: [
          {
            weight: 100
            latestRevision: true
          }
        ]
      }
      registries: [
        {
          server: '${resourcePrefix}acr.azurecr.io'
          username: '${resourcePrefix}acr'
          passwordSecretRef: 'acr-password'
        }
      ]
      secrets: [
        {
          name: 'acr-password'
          value: containerRegistry.listCredentials().passwords[0].value
        }
        {
          name: 'cosmos-connection-string'
          value: 'AccountEndpoint=${cosmosAccount.properties.documentEndpoint};AccountKey=${cosmosAccount.listKeys().primaryMasterKey};'
        }
        {
          name: 'form-recognizer-endpoint'
          value: formRecognizerAccount.properties.endpoint
        }
        {
          name: 'form-recognizer-key'
          value: formRecognizerAccount.listKeys().key1
        }
        {
          name: 'openai-endpoint'
          value: openaiAccount.properties.endpoint
        }
        {
          name: 'openai-key'
          value: openaiAccount.listKeys().key1
        }
        {
          name: 'cognitive-search-endpoint'
          value: searchService.properties.searchEndpoint
        }
        {
          name: 'cognitive-search-key'
          value: searchService.listAdminKeys().primaryKey
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'ai-processing'
          image: '${resourcePrefix}acr.azurecr.io/ai-processing:latest'
          resources: {
            cpu: json('1.0')
            memory: '2Gi'
          }
          env: [
            {
              name: 'FORM_RECOGNIZER_ENDPOINT'
              secretRef: 'form-recognizer-endpoint'
            }
            {
              name: 'FORM_RECOGNIZER_KEY'
              secretRef: 'form-recognizer-key'
            }
            {
              name: 'OPENAI_ENDPOINT'
              secretRef: 'openai-endpoint'
            }
            {
              name: 'OPENAI_API_KEY'
              secretRef: 'openai-key'
            }
            {
              name: 'COGNITIVE_SEARCH_ENDPOINT'
              secretRef: 'cognitive-search-endpoint'
            }
            {
              name: 'COGNITIVE_SEARCH_KEY'
              secretRef: 'cognitive-search-key'
            }
            {
              name: 'COSMOS_CONNECTION_STRING'
              secretRef: 'cosmos-connection-string'
            }
          ]
        }
      ]
      scale: {
        minReplicas: environment == 'dev' ? 1 : 2
        maxReplicas: environment == 'dev' ? 5 : 15
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '20'
              }
            }
          }
        ]
      }
    }
  }
}

resource analyticsApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: '${resourcePrefix}-analytics'
  location: location
  tags: tags
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8002
        allowInsecure: false
        traffic: [
          {
            weight: 100
            latestRevision: true
          }
        ]
      }
      registries: [
        {
          server: '${resourcePrefix}acr.azurecr.io'
          username: '${resourcePrefix}acr'
          passwordSecretRef: 'acr-password'
        }
      ]
      secrets: [
        {
          name: 'acr-password'
          value: containerRegistry.listCredentials().passwords[0].value
        }
        {
          name: 'cosmos-connection-string'
          value: 'AccountEndpoint=${cosmosAccount.properties.documentEndpoint};AccountKey=${cosmosAccount.listKeys().primaryMasterKey};'
        }
        {
          name: 'application-insights-connection-string'
          value: applicationInsights.properties.ConnectionString
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'analytics'
          image: '${resourcePrefix}acr.azurecr.io/analytics:latest'
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            {
              name: 'COSMOS_CONNECTION_STRING'
              secretRef: 'cosmos-connection-string'
            }
            {
              name: 'APPLICATION_INSIGHTS_CONNECTION_STRING'
              secretRef: 'application-insights-connection-string'
            }
          ]
        }
      ]
      scale: {
        minReplicas: environment == 'dev' ? 1 : 2
        maxReplicas: environment == 'dev' ? 3 : 8
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '50'
              }
            }
          }
        ]
      }
    }
  }
}

resource apiGatewayApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: '${resourcePrefix}-api-gateway'
  location: location
  tags: tags
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8003
        allowInsecure: false
        traffic: [
          {
            weight: 100
            latestRevision: true
          }
        ]
      }
      registries: [
        {
          server: '${resourcePrefix}acr.azurecr.io'
          username: '${resourcePrefix}acr'
          passwordSecretRef: 'acr-password'
        }
      ]
      secrets: [
        {
          name: 'acr-password'
          value: containerRegistry.listCredentials().passwords[0].value
        }
        {
          name: 'jwt-secret-key'
          value: 'your-jwt-secret-key-here'
        }
        {
          name: 'key-vault-url'
          value: keyVault.properties.vaultUri
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'api-gateway'
          image: '${resourcePrefix}acr.azurecr.io/api-gateway:latest'
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            {
              name: 'JWT_SECRET_KEY'
              secretRef: 'jwt-secret-key'
            }
            {
              name: 'KEY_VAULT_URL'
              secretRef: 'key-vault-url'
            }
            {
              name: 'REDIS_CONNECTION_STRING'
              value: 'redis://${redisCache.properties.hostName}:6380,ssl=true'
            }
          ]
        }
      ]
      scale: {
        minReplicas: environment == 'dev' ? 1 : 2
        maxReplicas: environment == 'dev' ? 3 : 10
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '100'
              }
            }
          }
        ]
      }
    }
  }
}

// =============================================
// SUPPORTING RESOURCES
// =============================================

// Log Analytics Workspace
resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${resourcePrefix}-logs'
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: environment == 'dev' ? 30 : 90
  }
}

// Application Insights
resource applicationInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${resourcePrefix}-appinsights'
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalyticsWorkspace.id
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

// Container Registry
resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: '${resourcePrefix}acr'
  location: location
  tags: tags
  sku: {
    name: environment == 'dev' ? 'Basic' : 'Standard'
  }
  properties: {
    adminUserEnabled: true
  }
}

// Key Vault
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: '${resourcePrefix}-kv'
  location: location
  tags: tags
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: tenant().tenantId
    accessPolicies: []
    enabledForDeployment: false
    enabledForDiskEncryption: false
    enabledForTemplateDeployment: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    enableRbacAuthorization: true
    publicNetworkAccess: 'Enabled'
  }
}

// Redis Cache
resource redisCache 'Microsoft.Cache/Redis@2023-08-01' = {
  name: '${resourcePrefix}-redis'
  location: location
  tags: tags
  properties: {
    sku: {
      name: environment == 'dev' ? 'Basic' : 'Standard'
      family: 'C'
      capacity: environment == 'dev' ? 0 : 1
    }
    enableNonSslPort: false
    minimumTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'
  }
}

// Virtual Network
resource vnet 'Microsoft.Network/virtualNetworks@2023-05-01' = {
  name: '${resourcePrefix}-vnet'
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: [
        '10.0.0.0/16'
      ]
    }
    subnets: [
      {
        name: 'default'
        properties: {
          addressPrefix: '10.0.1.0/24'
        }
      }
    ]
  }
}

resource vnetSubnet 'Microsoft.Network/virtualNetworks/subnets@2023-05-01' = {
  parent: vnet
  name: 'default'
  properties: {
    addressPrefix: '10.0.1.0/24'
  }
}

// =============================================
// AI CHAT CONTAINER APP
// =============================================
resource aiChatApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: '${resourcePrefix}-ai-chat'
  location: location
  tags: tags
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8004
        allowInsecure: false
        traffic: [
          {
            weight: 100
            latestRevision: true
          }
        ]
      }
      registries: [
        {
          server: '${resourcePrefix}acr.azurecr.io'
          username: '${resourcePrefix}acr'
          passwordSecretRef: 'acr-password'
        }
      ]
      secrets: [
        {
          name: 'acr-password'
          value: containerRegistry.listCredentials().passwords[0].value
        }
        {
          name: 'openai-api-key'
          value: 'your-openai-api-key'
        }
        {
          name: 'cognitive-search-key'
          value: 'your-cognitive-search-key'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'ai-chat'
          image: '${resourcePrefix}acr.azurecr.io/ai-chat:latest'
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            {
              name: 'OPENAI_API_KEY'
              secretRef: 'openai-api-key'
            }
            {
              name: 'COGNITIVE_SEARCH_KEY'
              secretRef: 'cognitive-search-key'
            }
            {
              name: 'COSMOS_CONNECTION_STRING'
            }
            {
              name: 'STORAGE_CONNECTION_STRING'
              value: storageAccount.primaryEndpoints.blob
            }
          ]
        }
      ]
      scale: {
        minReplicas: environment == 'dev' ? 1 : 2
        maxReplicas: environment == 'dev' ? 3 : 10
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '50'
              }
            }
          }
        ]
      }
    }
  }
}

// =============================================
// OUTPUTS
// =============================================
output storageAccountName string = storageAccount.name
output storageAccountKey string = storageAccount.listKeys().keys[0].value
output dataLakeStorageAccountName string = dataLakeStorageAccount.name
output dataLakeStorageAccountKey string = dataLakeStorageAccount.listKeys().keys[0].value
output sqlServerName string = sqlServer.name
output sqlDatabaseName string = sqlDatabase.name
output sqlConnectionString string = 'Server=tcp:${sqlServer.properties.fullyQualifiedDomainName},1433;Initial Catalog=${sqlDatabase.name};Persist Security Info=False;User ID=sqladmin;Password=TempPassword123!;MultipleActiveResultSets=False;Encrypt=True;TrustServerCertificate=False;Connection Timeout=30;'
output eventHubConnectionString string = eventHubNamespace.listKeys().primaryConnectionString
output serviceBusConnectionString string = serviceBusNamespace.listKeys().primaryConnectionString
output formRecognizerEndpoint string = formRecognizerAccount.properties.endpoint
output formRecognizerKey string = formRecognizerAccount.listKeys().key1
output openaiEndpoint string = openaiAccount.properties.endpoint
output openaiKey string = openaiAccount.listKeys().key1
output searchEndpoint string = searchService.properties.searchEndpoint
output searchKey string = searchService.listAdminKeys().primaryKey
output applicationInsightsConnectionString string = applicationInsights.properties.ConnectionString
output keyVaultUri string = keyVault.properties.vaultUri
output redisHostName string = redisCache.properties.hostName
output containerRegistryLoginServer string = containerRegistry.properties.loginServer
output apiGatewayUrl string = 'https://${apiGatewayApp.properties.configuration.ingress.fqdn}'