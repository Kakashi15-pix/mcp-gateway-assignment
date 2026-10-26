[README (2).md](https://github.com/user-attachments/files/33982304/README.2.md)
# MCP Gateway on Kubernetes

A self-hostable **Model Context Protocol (MCP) gateway** for connecting, discovering, governing, and routing tools from multiple MCP servers through one authenticated endpoint.

The project combines a FastAPI gateway, a PostgreSQL-backed registry, a React administration dashboard, and three upstream MCP servers for WooCommerce, filesystem access, and Kubernetes health monitoring. Helm charts deploy the platform alongside a WordPress/WooCommerce store.

> **Project status:** Development / assignment implementation. The repository includes local-development instructions, test scripts, and Helm deployment examples. Review the security and production notes before exposing it to a shared network.

## Table of contents

- [Why this project](#why-this-project)
- [Architecture](#architecture)
- [Features](#features)
- [Technology stack](#technology-stack)
- [Repository structure](#repository-structure)
- [Prerequisites](#prerequisites)
- [Run locally](#run-locally)
- [Deploy with Minikube and Helm](#deploy-with-minikube-and-helm)
- [Gateway endpoints](#gateway-endpoints)
- [Available MCP tools](#available-mcp-tools)
- [Security model](#security-model)
- [Testing and validation](#testing-and-validation)
- [Troubleshooting](#troubleshooting)
- [Limitations and next steps](#limitations-and-next-steps)
- [Documentation](#documentation)
- [License](#license)

## Why this project

Connecting an AI client to several MCP servers individually creates extra configuration and makes access control, tool discovery, and monitoring harder to manage. This project places a gateway between clients and upstream servers so tool access can be managed centrally.

The gateway discovers tools advertised by registered MCP servers, stores their metadata in PostgreSQL, assigns public namespaced tool names, checks caller permissions and rate limits, routes calls to the appropriate upstream, and records outcomes in an audit log.

## Architecture

```text
                          +---------------------------+
                          | React / TypeScript UI     |
                          | dashboard.localhost       |
                          +-------------+-------------+
                                        | /api/*
                                        v
+-------------------+       +-----------+-------------+       +------------------+
| MCP Client        |------>| FastAPI MCP Gateway     |<----->| PostgreSQL       |
| MCP Inspector     |       | Auth / Policy / Router  |       | Registry / Users |
| Agent             |       | Discovery / Audit       |       | Tools / Audit    |
+-------------------+       +-----------+-------------+       +------------------+
                                        |
                        +---------------+----------------+
                        |               |                |
                        v               v                v
              +----------------+ +---------------+ +------------------+
              | WooCommerce MCP| | Filesystem MCP| | Kubernetes MCP   |
              | products/orders| | scoped files  | | cluster/pod health|
              +--------+-------+ +---------------+ +------------------+
                       |
                       v
              +-----------------------------+
              | WordPress + WooCommerce     |
              | MariaDB                     |
              +-----------------------------+

         Helm charts manage the store and platform deployments.
```

### Request lifecycle

1. An administrator registers an upstream MCP server and its Streamable HTTP endpoint.
2. The gateway connects to that endpoint and discovers the tools and input schemas the server advertises.
3. Tool metadata is synchronized to PostgreSQL. Public names are namespaced by server ID, for example `woocommerce__list_products`.
4. The gateway authenticates an MCP client using an API key and filters tools according to role- or user-level permissions.
5. Calls pass through permission and rate-limit checks before the router forwards them to the appropriate upstream server.
6. The gateway records results and timing information. A background health loop periodically rechecks enabled servers and refreshes discovery.

## Features

- **Single MCP entry point** for discovered tools from multiple upstream MCP servers.
- **Dynamic discovery and synchronization** of tool names, descriptions, and input schemas.
- **Namespaced tool identifiers** to reduce collisions across upstream servers.
- **Authentication** with login sessions for the dashboard/API and bearer API keys for MCP clients.
- **Server administration** to register, inspect, enable, disable, sync, and remove servers.
- **Role- and user-level permissions** for governing which tools callers can discover and execute.
- **Rate-limit policies** backed by an in-memory limiter.
- **Audit logging** for tool-call outcomes and durations.
- **Upstream credential references** for bearer or custom-header authentication.
- **Health endpoints** for liveness and database readiness.
- **Admin dashboard** for servers, API keys, members, permissions, available tools, and audit history.
- **WooCommerce integration** for product and order operations.
- **Filesystem integration** with root-directory confinement and bounded reads/search results.
- **Kubernetes integration** for cluster status, pod details, and unhealthy-pod inspection.
- **Helm charts** for the WordPress/WooCommerce store and the MCP platform.

## Technology stack

| Area | Technologies |
| --- | --- |
| Gateway | Python, FastAPI, MCP Python SDK, Uvicorn |
| Database and migrations | PostgreSQL, SQLAlchemy, Alembic, Psycopg |
| Admin dashboard | React, TypeScript, Vite, TanStack Query, Tailwind CSS |
| Store integration | WordPress, WooCommerce REST API, MariaDB |
| Containers | Docker, Docker Compose |
| Orchestration | Kubernetes, Minikube, Helm |
| Kubernetes client | Python Kubernetes client |

## Repository structure

```text
.
├── gateway/                 # Gateway API, authentication, discovery, routing and migrations
│   ├── main.py              # FastAPI app and mounted MCP endpoint
│   ├── auth.py              # Sessions, API keys and password helpers
│   ├── discovery.py         # Upstream tool discovery/synchronization
│   ├── router.py            # Routes namespaced tool calls to upstreams
│   ├── permissions.py       # Tool permissions and audit helpers
│   ├── ratelimiter.py       # In-memory rate limiter
│   ├── models.py            # SQLAlchemy database models
│   ├── alembic/             # Database migration history
│   └── requirements.txt
├── dashboard/               # React + TypeScript admin dashboard
├── wc-server.py             # WooCommerce MCP server
├── fs-server.py             # Filesystem MCP server
├── k8s-server.py            # Kubernetes health MCP server
├── wc-server/               # WooCommerce MCP image build context
├── fs-server/               # Filesystem MCP image build context
├── k8s-server/              # Kubernetes MCP image build context
├── charts/
│   ├── store/               # WordPress/WooCommerce + MariaDB Helm chart
│   └── platform/            # Gateway, dashboard, PostgreSQL and MCP servers
├── mcp-files/               # Sample filesystem-server data
├── compose.yaml             # WordPress + MariaDB development stack
└── requirements.txt         # Root-level MCP/Kubernetes Python dependencies
```

## Prerequisites

For local development, install:

- Python compatible with the included dependencies (the Docker images use Python 3.12)
- Node.js and npm for the dashboard
- PostgreSQL 16 for the gateway database
- Git
- Docker Desktop / Docker Engine if using Compose or containers

For Kubernetes deployment, also install Minikube or another Kubernetes cluster, `kubectl`, Helm 3, and an ingress controller if you want to use the configured hostnames.

## Run locally

These steps run the services as separate development processes. The root `compose.yaml` is **only** the WordPress/MariaDB stack; it does not start the gateway, its PostgreSQL database, or the MCP servers.

### 1. Clone the repository

```powershell
git clone https://github.com/Kakashi15-pix/mcp-gateway-assignment.git
cd mcp-gateway-assignment
```

### 2. Start PostgreSQL for the gateway

The gateway database is defined in `gateway/compose.yaml`. It publishes PostgreSQL on host port `5433` and requires `DB_PASSWORD` in the environment.

```powershell
$env:DB_PASSWORD = "replace-with-a-local-password"
docker compose -f .\gateway\compose.yaml up -d
```

### 3. Configure gateway environment variables

Create `gateway/.env` locally. Do not commit this file or any production credentials.

```dotenv
DB_USER=gateway_user
DB_PASSWORD=replace-with-a-local-password
DB_HOST=127.0.0.1
DB_PORT=5433
DB_NAME=mcp_gateway

ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=replace-with-a-strong-local-password

# Optional local transport / dashboard settings
MCP_PUBLIC_HOSTS=localhost,127.0.0.1
DASHBOARD_BASE_URL=http://127.0.0.1:3000
CORS_ORIGINS=http://127.0.0.1:3000

# Optional OpenAI-compatible provider settings for the gateway chat endpoint
LLM_BASE_URL=
LLM_MODEL=
LLM_API_KEY=
```

The gateway uses `python-dotenv` to load environment variables. Confirm that local `.env` files are ignored by Git before adding credentials.

### 4. Install gateway dependencies, migrate, and create the admin account

```powershell
cd gateway
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
alembic upgrade head
python seed_admin.py
```

Run the gateway on port `9000`:

```powershell
uvicorn main:app --host 127.0.0.1 --port 9000 --reload
```

Keep this terminal running. The dashboard's development proxy defaults to `http://127.0.0.1:9000`.

### 5. Start the dashboard

In a separate terminal from the repository root:

```powershell
cd dashboard
npm install
$env:GATEWAY_PROXY_TARGET = "http://127.0.0.1:9000"
$env:VITE_GATEWAY_URL = "http://127.0.0.1:9000/mcp/"
npm run dev
```

Open [http://127.0.0.1:3000](http://127.0.0.1:3000).

### 6. Start the upstream MCP servers

Run each server in a separate terminal. The gateway must be able to reach the URLs you register. If the gateway runs in a container, `127.0.0.1` refers to that container itself, not the host or another container; use the appropriate service name or host-reachable address instead.

#### Filesystem server — port 8002

By default, the server uses the repository's `mcp-files/` directory. Set `FS_ROOT` to change the root.

```powershell
$env:HOST = "127.0.0.1"
$env:PORT = "8002"
python fs-server.py
```

If `MCP_AUTH_TOKEN` is configured, requests other than `/health` require the matching bearer token.

#### Kubernetes health server — port 8001

The server loads in-cluster Kubernetes credentials when available, otherwise it uses the local kubeconfig.

```powershell
$env:HOST = "127.0.0.1"
$env:PORT = "8001"
python k8s-server.py
```

Make sure the active Kubernetes context is the intended cluster and has permissions to list nodes and pods.

#### WooCommerce server — port 8003

This server requires valid WooCommerce REST API credentials. The store URL must be reachable from the process running this MCP server.

```powershell
$env:HOST = "127.0.0.1"
$env:PORT = "8003"
$env:WC_STORE_URL = "http://shop.localhost"
$env:WC_CONSUMER_KEY = "your-consumer-key"
$env:WC_CONSUMER_SECRET = "your-consumer-secret"
python wc-server.py
```

### 7. Register upstream servers

Sign in to the dashboard as an administrator, open **Servers**, and register each server using its reachable Streamable HTTP MCP endpoint. Typical local URLs are:

| Server ID | MCP endpoint | Tools |
| --- | --- | --- |
| `filesystem` | `http://127.0.0.1:8002/mcp/` | `list_files`, `read_file`, `search_files` |
| `kubernetes` | `http://127.0.0.1:8001/mcp/` | `get_cluster_health`, `get_pod_details`, `list_unhealthy_pods` |
| `woocommerce` | `http://127.0.0.1:8003/mcp/` | `list_products`, `get_product`, `list_orders`, `get_order`, `create_product`, `update_order_status` |

Use the exact endpoint path served by the upstream; URLs ending in `/mcp` are normalized by the gateway to include a trailing slash. Use the **Sync** action after registration to refresh the tool catalog.

## Deploy with Minikube and Helm

The repository includes two charts: `charts/store` for WordPress/WooCommerce and MariaDB, and `charts/platform` for PostgreSQL, the gateway, dashboard, and MCP servers. The platform chart is designed to run alongside the store chart. Read the chart-specific guides before deployment:

- [Store chart guide](charts/store/README.md)
- [Platform chart guide](charts/platform/README.md)

### 1. Start Minikube and ingress

```powershell
minikube start --driver=docker
minikube addons enable ingress
```

If your local ingress setup requires it, run `minikube tunnel` in a separate terminal. Reuse your existing Minikube profile if it is already configured.

### 2. Build local service images

The local platform values use these image names and tags. Check the chart values and Dockerfiles if you have changed them.

```powershell
docker build -t mcp-gateway:host6 -f .\gateway\Dockerfile .\gateway
docker build -t mcp-dashboard:dev .\dashboard
docker build -t woo-mcp:dev -f .\wc-server\Dockerfile .
docker build -t filesystem-mcp:dev -f .\fs-server\Dockerfile .
docker build -t kubernetes-mcp:dev -f .\k8s-server\Dockerfile .
```

Load them into Minikube:

```powershell
minikube image load mcp-gateway:host6
minikube image load mcp-dashboard:dev
minikube image load woo-mcp:dev
minikube image load filesystem-mcp:dev
minikube image load kubernetes-mcp:dev
```

### 3. Install the store and platform

The platform chart expects its database and optional LLM configuration to be supplied through the configured values/Secrets. If the platform consumes the WooCommerce REST Secret generated by the store chart, install the store first and verify the Secret name expected by the platform chart. Do not commit secret-bearing values files.

```powershell
helm upgrade --install store .\charts\store --namespace store --create-namespace `
  -f .\charts\store\values-local.yaml

helm upgrade --install platform .\charts\platform --namespace store `
  -f .\charts\platform\values-local.yaml
```

Review `charts/platform/values-local.yaml` before applying it: the sample store hostname/IP is environment-specific and may need to be updated for your current Minikube cluster.

### 4. Verify the deployment

```powershell
kubectl get pods -n store
kubectl get deployments -n store
kubectl get svc -n store
kubectl get ingress -n store
kubectl get events -n store --sort-by=.lastTimestamp
```

For a workload that is not ready:

```powershell
kubectl describe pod <pod-name> -n store
kubectl logs <pod-name> -n store
kubectl get pvc -n store
```

The supplied local ingress values use `dashboard.localhost` for the dashboard and `shop.localhost` for the store. If these names do not resolve correctly in your environment, use the ingress instructions in the chart documentation.

## Gateway endpoints

For the local gateway started on port `9000`:

| Purpose | Endpoint | Authentication |
| --- | --- | --- |
| Liveness | `GET /healthz` | None |
| Database readiness | `GET /readyz` | None |
| MCP endpoint | `http://127.0.0.1:9000/mcp/` | MCP API key |
| Tool list | `GET /tools` | MCP API key |
| Session-visible tools | `GET /tools/available` | Dashboard/session token |
| Login | `POST /auth/login` | Credentials in request body |
| Server registry | `/admin/servers` | Admin session |
| Permissions | `/admin/permissions` | Admin session |
| Rate-limit policies | `/admin/rate-limits` | Admin session |
| Audit history | `/admin/audit`, `/audit` | Admin or session, depending on route |

### Connect an MCP client

Use the gateway endpoint, not an individual upstream server:

```text
http://127.0.0.1:9000/mcp/
```

Configure the MCP client to send the key created through the dashboard as a bearer token:

```http
Authorization: Bearer <MCP_API_KEY>
```

The raw API key is shown only when it is created. Copy it at that time and store it securely. A dashboard session token and an MCP API key are different credentials.

## Available MCP tools

### WooCommerce

| Tool | Purpose |
| --- | --- |
| `list_products` | List products with optional search and pagination. |
| `get_product` | Retrieve a product by ID. |
| `list_orders` | List orders with date/status filters and pagination. |
| `get_order` | Retrieve order details, including line items. |
| `create_product` | Create a simple product. |
| `update_order_status` | Change an order status. |

Environment variables: `WC_STORE_URL`, `WC_CONSUMER_KEY`, and `WC_CONSUMER_SECRET`. The create/update tools modify store data; test against a local/demo store first.

### Filesystem

| Tool | Purpose |
| --- | --- |
| `list_files` | List files and directories under the configured root. |
| `read_file` | Read UTF-8 text files, with a bounded read size. |
| `search_files` | Search file names and text content. |

Set `FS_ROOT` to restrict the server to the directory intended for MCP access. The server rejects paths that resolve outside that root.

### Kubernetes

| Tool | Purpose |
| --- | --- |
| `get_cluster_health` | Report API accessibility, node readiness, and unhealthy pods. |
| `get_pod_details` | Show pod phase, readiness, container states, and restart counts. |
| `list_unhealthy_pods` | Find pending, failed, or unready pods, optionally by namespace. |

The actions available to this server depend on its Kubernetes identity and RBAC. Grant only the permissions needed for the intended monitoring tasks.

## Security model

- **Session authentication** protects dashboard/session-based API routes.
- **API key authentication** protects the gateway MCP endpoint and API-key tool listing.
- **Tool permissions** restrict tool visibility and execution by role or user.
- **Rate limits** reduce the frequency of calls according to configured policies.
- **Audit records** retain tool-call outcomes and timing information.
- **Upstream URL validation and transport host checks** help restrict gateway connections and MCP transport access.
- **Filesystem root checks** prevent file operations from escaping the configured root.
- **Kubernetes RBAC** controls what the Kubernetes MCP server can inspect or change.

### Deployment recommendations

- Never commit `.env` files, raw API keys, database passwords, admin passwords, WooCommerce secrets, or secret-bearing Helm values.
- Use strong unique credentials and rotate any credential that may have been exposed.
- Use TLS and a trusted ingress/reverse proxy outside local development.
- Register only trusted upstream MCP servers and protect upstream credentials.
- Keep Kubernetes RBAC minimal; monitoring-only scenarios generally should not have write privileges.
- Treat WooCommerce product/order modification tools as write access.
- Remember that rate-limit state is in memory: counters are process-local, reset on restart, and are not shared across replicas.

## Testing and validation

The repository includes gateway test scripts and standalone server connectivity checks. Run them after setting required environment variables and starting the services they depend on.

Gateway tests (run from `gateway/`):

```powershell
python test-registry.py
python test_discovery.py
python test_router.py
python test_failure_isolation.py
python test_visibility.py
```

Standalone server checks (run from the repository root):

```powershell
python fs-server-test.py
python k8s-server-test.py
python wc-server-test.py
```

Some tests require a live database, a running upstream MCP server, WooCommerce credentials, or a valid Kubernetes context. Review each test script for its specific setup requirements.

Validate the Helm charts before installing:

```powershell
helm lint .\charts\store
helm lint .\charts\platform
helm template store .\charts\store -n store -f .\charts\store\values-local.yaml
helm template platform .\charts\platform -n store -f .\charts\platform\values-local.yaml
```

For an end-to-end check, verify that tools are discovered, unauthorized or disabled tools are not exposed to members, allowed calls reach the intended upstream, an unavailable upstream does not break unrelated servers, and audit events are recorded.

## Troubleshooting

### `401 Invalid API key`

- Confirm that the full raw API key was copied when it was created.
- Confirm it belongs to an active user and has not expired or been revoked.
- Send it as `Authorization: Bearer <MCP_API_KEY>`; a dashboard session token is not an MCP API key.
- Check that the request targets the intended gateway instance and database.

### MCP Inspector returns `404 Not Found`

- Use the gateway URL ending in `/mcp/`, including the trailing slash.
- Make sure the configured URL points to the gateway and not to an upstream server.
- Confirm the gateway is running and configure the MCP API key as a bearer token.
- Inspect the gateway logs and verify the exact URL entered in the inspector.

### A registered server has no tools

- Check that the upstream MCP URL is reachable **from the gateway process/container**.
- Register the MCP endpoint, not only the server's root URL.
- Use **Sync** in the dashboard and inspect the server status, last error, and gateway logs.
- Verify credentials and transport host settings on the upstream server.

### Gateway readiness fails

- Check PostgreSQL is running and `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, and `DB_NAME` match the database.
- From `gateway/`, run `alembic upgrade head`.
- Review logs for database connection or migration errors.

### Kubernetes MCP server cannot reach the cluster

- Check `kubectl config current-context` and `kubectl get nodes`.
- For in-cluster deployment, verify the service account's RBAC permissions.
- Inspect the server pod logs and namespace events.

### WooCommerce REST requests return `401` or `404`

- Verify WooCommerce is active and the REST consumer key/secret are valid.
- Confirm the store URL is reachable from the WooCommerce MCP server environment.
- Verify the key's permissions and WordPress permalink/API configuration.

### A Helm workload does not become ready

Run:

```powershell
kubectl get pods -n store
kubectl get pvc -n store
kubectl get events -n store --sort-by=.lastTimestamp
kubectl describe pod <pod-name> -n store
kubectl logs <pod-name> -n store
```

Look for pending storage claims, image-pull failures, failed probes, missing Secrets, and outdated host/IP values.

## Limitations and next steps

- The dashboard's Chat page is currently a placeholder; the backend chat endpoint should not be confused with a completed dashboard chat workflow.
- Rate limiting is in-memory and is not shared across gateway replicas.
- Local image tags and sample IP/host values are development defaults and must be reviewed for other environments.
- Before production use, review secret management, TLS, authorization policy, network policy, backups, resource limits, logging/monitoring, and Kubernetes RBAC.

## Documentation

- [Dashboard guide and manual test list](dashboard/README.md)
- [Store Helm chart guide](charts/store/README.md)
- [Platform Helm chart guide](charts/platform/README.md)

## License

No license file is currently included. Until a license is added, default copyright restrictions apply to reuse and redistribution.
