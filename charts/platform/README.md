# Platform Helm chart

This chart installs Postgres, the MCP gateway, dashboard, and the WooCommerce,
filesystem, and Kubernetes MCP servers into the `store` namespace. It is Helm
only and is designed to run next to the `charts/store` release.

## Install locally

Build the images from the repository root, then load them into the local
cluster and install both charts:

```powershell
helm upgrade --install store .\charts\store --namespace store --create-namespace `
  -f .\charts\store\values-local.yaml
helm upgrade --install platform .\charts\platform --namespace store `
  -f .\charts\platform\values-local.yaml
```

For a local ingress controller, map the domain before opening the dashboard:

```text
127.0.0.1 dashboard.localhost
```

The store chart's WooCommerce API Secret must exist as `store-wc-api` before
the platform release is installed.

## VPS install

Use the production values with image repositories reachable by the cluster and
provide the existing Postgres and LLM Secrets:

```powershell
helm upgrade --install store .\charts\store --namespace store --create-namespace `
  -f .\charts\store\values-prod.yaml
helm upgrade --install platform .\charts\platform --namespace store `
  -f .\charts\platform\values-prod.yaml
```

Local values use development image tags, small persistent storage, and the
`dashboard.localhost` host. Production values use registry image references,
larger storage, existing credentials, and a routable dashboard host. Both
environments use the same templates and services.
