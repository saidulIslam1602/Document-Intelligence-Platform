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
// COSMOS DB
// =============================================
resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2023-09-15' = {
  name: '${resourcePrefix}-cosmos'
  location: location
  tags: tags
  kind: 'GlobalDocumentDB'
  properties: {
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    databaseAccountOfferType: 'Standard'
    enableAutomaticFailover: true
    enableMultipleWriteLocations: false
    isVirtualNetworkFilterEnabled: false
    virtualNetworkRules: []
    ipRules: []
    enableFreeTier: environment == 'dev' ? true : false
    capabilities: [
      {
        name: 'EnableServerless'
      }
    ]
  }
}

resource cosmosDatabase 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2023-09-15' = {
  parent: cosmosAccount
  name: 'documentdb'
  properties: {
    resource: {
      id: 'documentdb'
    }
  }
}

// Cosmos DB containers
resource documentsContainerCosmos 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-09-15' = {
  parent: cosmosDatabase
  name: 'documents'
  properties: {
    resource: {
      id: 'documents'
      partitionKey: {
        paths: ['/partition_key']
        kind: 'Hash'
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        includedPaths: [
          {
            path: '/*'
          }
        ]
        excludedPaths: [
          {
            path: '/"_etag"/?'
          }
        ]
      }
    }
  }
}

resource analyticsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-09-15' = {
  parent: cosmosDatabase
  name: 'analytics'
  properties: {
    resource: {
      id: 'analytics'
      partitionKey: {
        paths: ['/partition_key']
        kind: 'Hash'
      }
    }
  }
}

resource eventsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-09-15' = {
  parent: cosmosDatabase
  name: 'events'
  properties: {
    resource: {
      id: 'events'
      partitionKey: {
        paths: ['/partition_key']
        kind: 'Hash'
      }
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
// OUTPUTS
// =============================================
output storageAccountName string = storageAccount.name
output storageAccountKey string = storageAccount.listKeys().keys[0].value
output cosmosAccountEndpoint string = cosmosAccount.properties.documentEndpoint
output cosmosAccountKey string = cosmosAccount.listKeys().primaryMasterKey
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