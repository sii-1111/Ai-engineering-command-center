# Azure deployment architecture

Production-style topology for the AI Engineering Command Center.

## Runtime

- Azure Container Registry: application images.
- Azure Container Apps: Next.js web, FastAPI API, and Redis-backed worker.
- Azure Database for PostgreSQL Flexible Server: durable task/checkpoint state.
- Azure Managed Redis: job state and worker coordination.
- Azure Key Vault: runtime secrets.
- Log Analytics: application logs.
- Existing Azure AI Search and Blob Storage remain external provider resources.

## Deployment

The Bicep template defaults to `deployApps=false`, allowing infrastructure to be provisioned before application images exist.

```bash
az group create --name aicc-prod --location centralindia

az deployment group create \
  --resource-group aicc-prod \
  --template-file infra/azure/main.bicep \
  --parameters postgresAdminPassword='<secret>'
```

After images are pushed to the emitted ACR, deploy the applications with secure values for the database, Redis, GitHub, Azure OpenAI, Search, and Blob integrations:

```bash
az deployment group create \
  --resource-group aicc-prod \
  --template-file infra/azure/main.bicep \
  --parameters \
    postgresAdminPassword='<secret>' \
    deployApps=true \
    apiImage='<acr>.azurecr.io/aicc-api:<git-sha>' \
    workerImage='<acr>.azurecr.io/aicc-worker:<git-sha>' \
    webImage='<acr>.azurecr.io/aicc-web:<git-sha>'
```

Never commit passwords, API keys, tokens, or connection strings.

## CI safety

This milestone does **not** modify `.github/workflows/ci.yml`. Existing Python lint/tests and the Next.js build remain the pull-request validation contract.

Azure deployment is intentionally separate from PR CI because it requires subscription credentials, environment-specific secrets, image availability, and a target Azure resource group.

## Security boundary

This is deployment topology, not the final hardening milestone. Private networking, private endpoints, workload-specific identities, egress controls, WAF/API gateway policy, and stricter database/registry network controls remain part of the later enterprise-security milestone.

The PostgreSQL Azure-services firewall rule is therefore a bootstrap-compatible setting and should be tightened before a real production rollout.

## Validation

Before a subscription deployment, validate:

```bash
az bicep build --file infra/azure/main.bicep
az deployment group what-if \
  --resource-group aicc-prod \
  --template-file infra/azure/main.bicep \
  --parameters postgresAdminPassword='<secret>'
```
