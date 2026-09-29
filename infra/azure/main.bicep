targetScope = 'resourceGroup'

@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Short deployment name.')
param namePrefix string = 'aicc'

@description('Deploy Container Apps after images and secrets are available.')
param deployApps bool = false

@description('Enable private networking for PostgreSQL, Key Vault, and ACR. Requires Premium ACR.')
param enablePrivateNetworking bool = true

@description('PostgreSQL administrator login.')
param postgresAdminLogin string = 'aiccadmin'

@secure()
@description('PostgreSQL administrator password.')
param postgresAdminPassword string

@description('FastAPI container image.')
param apiImage string = ''

@description('Background worker container image.')
param workerImage string = ''

@description('Next.js web container image.')
param webImage string = ''

@description('Public web origin used by the API.')
param webOrigin string = ''

@description('Existing Azure AI Search endpoint.')
param azureSearchEndpoint string = ''

@description('Existing Azure OpenAI endpoint.')
param azureOpenAiEndpoint string = ''

@description('Azure OpenAI deployment name.')
param azureOpenAiDeployment string = ''

@secure()
@description('Existing Azure Blob Storage connection string, when required.')
param azureStorageConnectionString string = ''

@secure()
@description('GitHub token used by the MCP integration.')
param githubToken string = ''

@secure()
@description('Azure OpenAI API key, when Entra ID is not used.')
param azureOpenAiApiKey string = ''

@secure()
@description('Azure AI Search API key, when Entra ID is not used.')
param azureSearchApiKey string = ''

@secure()
@description('Complete PostgreSQL connection URL for the application.')
param databaseUrl string = ''

@secure()
@description('Complete Redis connection URL for the application.')
param redisUrl string = ''

var suffix = uniqueString(resourceGroup().id, namePrefix)
var acrName = toLower('${namePrefix}acr${take(suffix, 8)}')
var logName = '${namePrefix}-logs-${take(suffix, 6)}'
var envName = '${namePrefix}-aca-${take(suffix, 6)}'
var keyVaultName = '${namePrefix}-kv-${take(suffix, 8)}'
var postgresName = '${namePrefix}-pg-${take(suffix, 8)}'
var redisName = '${namePrefix}-redis-${take(suffix, 8)}'
var identityName = '${namePrefix}-runtime-${take(suffix, 8)}'
var vnetName = '${namePrefix}-vnet-${take(suffix, 6)}'
var acaSubnetName = 'aca-infra'
var postgresSubnetName = 'postgres'
var privateEndpointSubnetName = 'private-endpoints'
var postgresDnsName = '${namePrefix}.postgres.database.azure.com'

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logName
  location: location
  properties: {
    retentionInDays: 30
    sku: {
      name: 'PerGB2018'
    }
  }
}

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  sku: {
    name: enablePrivateNetworking ? 'Premium' : 'Basic'
  }
  properties: {
    adminUserEnabled: false
    publicNetworkAccess: enablePrivateNetworking ? 'Disabled' : 'Enabled'
  }
}

resource vnet 'Microsoft.Network/virtualNetworks@2024-05-01' = {
  name: vnetName
  location: location
  properties: {
    addressSpace: { addressPrefixes: [ '10.40.0.0/16' ] }
    subnets: [
      { name: acaSubnetName properties: { addressPrefix: '10.40.0.0/23' delegations: [{ name: 'container-apps' properties: { serviceName: 'Microsoft.App/environments' } }] } }
      { name: postgresSubnetName properties: { addressPrefix: '10.40.2.0/28' delegations: [{ name: 'postgres-flexible-server' properties: { serviceName: 'Microsoft.DBforPostgreSQL/flexibleServers' } }] } }
      { name: privateEndpointSubnetName properties: { addressPrefix: '10.40.3.0/27' privateEndpointNetworkPolicies: 'Disabled' } }
    ]
  }
}

resource postgresPrivateDns 'Microsoft.Network/privateDnsZones@2024-06-01' = if (enablePrivateNetworking) {
  name: postgresDnsName
  location: 'global'
}
resource postgresDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = if (enablePrivateNetworking) {
  parent: postgresPrivateDns
  name: 'vnet-link'
  properties: { registrationEnabled: false virtualNetwork: { id: vnet.id } }
}
resource acrPrivateDns 'Microsoft.Network/privateDnsZones@2024-06-01' = if (enablePrivateNetworking) {
  name: 'privatelink.azurecr.io'
  location: 'global'
}
resource acrDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = if (enablePrivateNetworking) {
  parent: acrPrivateDns
  name: 'vnet-link'
  properties: { registrationEnabled: false virtualNetwork: { id: vnet.id } }
}
resource keyVaultPrivateDns 'Microsoft.Network/privateDnsZones@2024-06-01' = if (enablePrivateNetworking) {
  name: 'privatelink.vaultcore.azure.net'
  location: 'global'
}
resource keyVaultDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = if (enablePrivateNetworking) {
  parent: keyVaultPrivateDns
  name: 'vnet-link'
  properties: { registrationEnabled: false virtualNetwork: { id: vnet.id } }
}

resource runtimeIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: identityName
  location: location
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  properties: {
    tenantId: tenant().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    publicNetworkAccess: 'Enabled'
  }
}

resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: postgresName
  location: location
  sku: {
    name: 'Standard_D2ds_v5'
    tier: 'GeneralPurpose'
  }
  properties: {
    administratorLogin: postgresAdminLogin
    administratorLoginPassword: postgresAdminPassword
    version: '16'
    storage: {
      storageSizeGB: 64
      autoGrow: 'Enabled'
      type: 'Premium_LRS'
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
    network: {
      publicNetworkAccess: enablePrivateNetworking ? 'Disabled' : 'Enabled'
      delegatedSubnetResourceId: enablePrivateNetworking ? resourceId('Microsoft.Network/virtualNetworks/subnets', vnet.name, postgresSubnetName) : null
      privateDnsZoneArmResourceId: enablePrivateNetworking ? postgresPrivateDns.id : null
    }
  }
}

resource postgresDatabase 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2024-08-01' = {
  parent: postgres
  name: 'command_center'
  properties: {
    charset: 'UTF8'
    collation: 'en_US.UTF8'
  }
}

resource postgresAzureServicesFirewall 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2024-08-01' = if (!enablePrivateNetworking) {
  parent: postgres
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

resource acrPrivateEndpoint 'Microsoft.Network/privateEndpoints@2024-05-01' = if (enablePrivateNetworking) {
  name: '${namePrefix}-acr-pe-${take(suffix, 6)}'
  location: location
  properties: {
    subnet: { id: resourceId('Microsoft.Network/virtualNetworks/subnets', vnet.name, privateEndpointSubnetName) }
    privateLinkServiceConnections: [{ name: 'acr' properties: { privateLinkServiceId: registry.id groupIds: [ 'registry' ] } }]
  }
}
resource keyVaultPrivateEndpoint 'Microsoft.Network/privateEndpoints@2024-05-01' = if (enablePrivateNetworking) {
  name: '${namePrefix}-kv-pe-${take(suffix, 6)}'
  location: location
  properties: {
    subnet: { id: resourceId('Microsoft.Network/virtualNetworks/subnets', vnet.name, privateEndpointSubnetName) }
    privateLinkServiceConnections: [{ name: 'keyvault' properties: { privateLinkServiceId: keyVault.id groupIds: [ 'vault' ] } }]
  }
}
resource acrPrivateDnsGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = if (enablePrivateNetworking) {
  parent: acrPrivateEndpoint
  name: 'default'
  properties: { privateDnsZoneConfigs: [{ name: 'acr' properties: { privateDnsZoneId: acrPrivateDns.id } }] }
}
resource keyVaultPrivateDnsGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = if (enablePrivateNetworking) {
  parent: keyVaultPrivateEndpoint
  name: 'default'
  properties: { privateDnsZoneConfigs: [{ name: 'keyvault' properties: { privateDnsZoneId: keyVaultPrivateDns.id } }] }
}

resource redis 'Microsoft.Cache/redisEnterprise@2025-04-01' = {
  name: redisName
  location: location
  sku: {
    name: 'Balanced_B0'
  }
  properties: {
    highAvailability: 'Enabled'
    minimumTlsVersion: '1.2'
    encryption: {}
  }
}

resource redisDatabase 'Microsoft.Cache/redisEnterprise/databases@2025-04-01' = {
  parent: redis
  name: 'default'
  properties: {
    clientProtocol: 'Encrypted'
    clusteringPolicy: 'EnterpriseCluster'
    evictionPolicy: 'NoEviction'
    modules: []
  }
}

resource containerEnvironment 'Microsoft.App/managedEnvironments@2025-07-01' = {
  name: envName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
    vnetConfiguration: {
      infrastructureSubnetId: resourceId('Microsoft.Network/virtualNetworks/subnets', vnet.name, acaSubnetName)
      internal: false
    }
  }
}

resource acrPullRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (deployApps) {
  name: guid(registry.id, runtimeIdentity.id, 'AcrPull')
  scope: registry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
    principalId: runtimeIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource keyVaultSecretsRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (deployApps) {
  name: guid(keyVault.id, runtimeIdentity.id, 'KeyVaultSecretsUser')
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6')
    principalId: runtimeIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource databaseUrlSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (deployApps && !empty(databaseUrl)) {
  parent: keyVault
  name: 'database-url'
  properties: {
    value: databaseUrl
  }
}

resource redisUrlSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (deployApps && !empty(redisUrl)) {
  parent: keyVault
  name: 'redis-url'
  properties: {
    value: redisUrl
  }
}

resource githubTokenSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (deployApps && !empty(githubToken)) {
  parent: keyVault
  name: 'github-token'
  properties: {
    value: githubToken
  }
}

resource azureOpenAiApiKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (deployApps && !empty(azureOpenAiApiKey)) {
  parent: keyVault
  name: 'azure-openai-api-key'
  properties: {
    value: azureOpenAiApiKey
  }
}

resource azureSearchApiKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (deployApps && !empty(azureSearchApiKey)) {
  parent: keyVault
  name: 'azure-search-api-key'
  properties: {
    value: azureSearchApiKey
  }
}

resource azureStorageConnectionStringSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (deployApps && !empty(azureStorageConnectionString)) {
  parent: keyVault
  name: 'azure-storage-connection-string'
  properties: {
    value: azureStorageConnectionString
  }
}

var commonSecrets = concat(
  !empty(databaseUrl) ? [{
    name: 'database-url'
    keyVaultUrl: '${keyVault.properties.vaultUri}secrets/database-url'
    identity: runtimeIdentity.id
  }] : [],
  !empty(redisUrl) ? [{
    name: 'redis-url'
    keyVaultUrl: '${keyVault.properties.vaultUri}secrets/redis-url'
    identity: runtimeIdentity.id
  }] : [],
  !empty(githubToken) ? [{
    name: 'github-token'
    keyVaultUrl: '${keyVault.properties.vaultUri}secrets/github-token'
    identity: runtimeIdentity.id
  }] : [],
  !empty(azureOpenAiApiKey) ? [{
    name: 'azure-openai-api-key'
    keyVaultUrl: '${keyVault.properties.vaultUri}secrets/azure-openai-api-key'
    identity: runtimeIdentity.id
  }] : [],
  !empty(azureSearchApiKey) ? [{
    name: 'azure-search-api-key'
    keyVaultUrl: '${keyVault.properties.vaultUri}secrets/azure-search-api-key'
    identity: runtimeIdentity.id
  }] : [],
  !empty(azureStorageConnectionString) ? [{
    name: 'azure-storage-connection-string'
    keyVaultUrl: '${keyVault.properties.vaultUri}secrets/azure-storage-connection-string'
    identity: runtimeIdentity.id
  }] : []
)

var commonEnv = concat(
  !empty(databaseUrl) ? [{
    name: 'DATABASE_URL'
    secretRef: 'database-url'
  }] : [],
  !empty(redisUrl) ? [{
    name: 'REDIS_URL'
    secretRef: 'redis-url'
  }] : [],
  !empty(githubToken) ? [{
    name: 'GITHUB_TOKEN'
    secretRef: 'github-token'
  }] : [],
  !empty(azureOpenAiApiKey) ? [{
    name: 'AZURE_OPENAI_API_KEY'
    secretRef: 'azure-openai-api-key'
  }] : [],
  !empty(azureSearchApiKey) ? [{
    name: 'AZURE_SEARCH_API_KEY'
    secretRef: 'azure-search-api-key'
  }] : [],
  !empty(azureStorageConnectionString) ? [{
    name: 'AZURE_STORAGE_CONNECTION_STRING'
    secretRef: 'azure-storage-connection-string'
  }] : [],
  !empty(azureOpenAiEndpoint) ? [{
    name: 'AZURE_OPENAI_ENDPOINT'
    value: azureOpenAiEndpoint
  }] : [],
  !empty(azureOpenAiDeployment) ? [{
    name: 'AZURE_OPENAI_DEPLOYMENT'
    value: azureOpenAiDeployment
  }] : [],
  !empty(azureSearchEndpoint) ? [{
    name: 'AZURE_SEARCH_ENDPOINT'
    value: azureSearchEndpoint
  }] : [],
  !empty(webOrigin) ? [{
    name: 'CORS_ORIGINS'
    value: webOrigin
  }] : []
)

resource api 'Microsoft.App/containerApps@2025-07-01' = if (deployApps) {
  name: '${namePrefix}-api'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${runtimeIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerEnvironment.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
        allowInsecure: false
      }
      registries: [
        {
          server: registry.properties.loginServer
          identity: runtimeIdentity.id
        }
      ]
      secrets: commonSecrets
    }
    template: {
      containers: [
        {
          name: 'api'
          image: apiImage
          resources: {
            cpu: 1
            memory: '2Gi'
          }
          env: commonEnv
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: 8000
              }
              initialDelaySeconds: 15
              periodSeconds: 30
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/health'
                port: 8000
              }
              initialDelaySeconds: 10
              periodSeconds: 15
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 5
        rules: [
          {
            name: 'http'
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

resource worker 'Microsoft.App/containerApps@2025-07-01' = if (deployApps) {
  name: '${namePrefix}-worker'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${runtimeIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerEnvironment.id
    configuration: {
      activeRevisionsMode: 'Single'
      registries: [
        {
          server: registry.properties.loginServer
          identity: runtimeIdentity.id
        }
      ]
      secrets: commonSecrets
    }
    template: {
      containers: [
        {
          name: 'worker'
          image: workerImage
          command: [
            'python'
            '-m'
            'core.workers.task_worker'
          ]
          resources: {
            cpu: 1
            memory: '2Gi'
          }
          env: commonEnv
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 5
      }
    }
  }
}

resource web 'Microsoft.App/containerApps@2025-07-01' = if (deployApps) {
  name: '${namePrefix}-web'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${runtimeIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerEnvironment.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 3000
        transport: 'auto'
        allowInsecure: false
      }
      registries: [
        {
          server: registry.properties.loginServer
          identity: runtimeIdentity.id
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'web'
          image: webImage
          resources: {
            cpu: 0.5
            memory: '1Gi'
          }
          env: [
            {
              name: 'NEXT_PUBLIC_API_URL'
              value: deployApps ? 'https://${api.properties.configuration.ingress.fqdn}' : ''
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
    }
  }
}

output resourceGroupName string = resourceGroup().name
output registryLoginServer string = registry.properties.loginServer
output keyVaultName string = keyVault.name
output containerEnvironmentName string = containerEnvironment.name
output postgresFqdn string = postgres.properties.fullyQualifiedDomainName
output redisHost string = redis.properties.hostName
output apiUrl string = deployApps ? 'https://${api.properties.configuration.ingress.fqdn}' : ''
output webUrl string = deployApps ? 'https://${web.properties.configuration.ingress.fqdn}' : ''
