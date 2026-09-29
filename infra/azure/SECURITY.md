# Enterprise security hardening

This milestone hardens the Azure deployment boundary without changing the repository CI workflow.

## Network controls

When `enablePrivateNetworking=true`:

- A dedicated VNet is created with separate Container Apps, PostgreSQL, and private-endpoint subnets.
- PostgreSQL Flexible Server uses delegated private access and private DNS.
- PostgreSQL public access is disabled; the bootstrap Azure-services firewall rule is removed.
- Azure Container Registry uses Premium SKU, disables public network access, and is reached through a private endpoint.
- Key Vault disables public network access and is reached through a private endpoint.
- Private DNS zones are linked to the VNet.
- Container Apps run on the VNet infrastructure subnet.
- Container Apps keep external ingress for the user-facing web/API surface; internal-only ingress is intentionally not enabled by default.

## Identity controls

- Container Apps pull images with a user-assigned managed identity.
- Key Vault secret reads use the managed identity and RBAC.
- ACR admin credentials remain disabled.

## Deployment safety

Private networking is enabled by default in this hardened template. A deployment that uses the hardened default therefore requires Azure networking capacity and Premium ACR.

The application still defaults to `deployApps=false`, so infrastructure can be created before application images exist.

## Deferred hardening

The following remain environment-specific or later-stage concerns:

- private connectivity to the existing Azure AI Search and Blob Storage resources
- private connectivity for the Redis service
- WAF/API gateway policy
- outbound egress allowlisting
- customer-managed keys
- separate managed identities for web, API, and worker
- production alerting and SIEM integration

These should be implemented against the actual target Azure environment rather than guessing existing resource IDs.

## CI

`.github/workflows/ci.yml` is unchanged.

Pull requests continue to run the existing Python lint/tests and Next.js build. Azure infrastructure deployment is not added to PR CI because it requires an Azure subscription and environment-specific credentials.
