# WooCommerce store Helm chart

This chart deploys a single-replica WordPress/WooCommerce storefront and a
single MariaDB StatefulSet. The database is ClusterIP-only and has a
NetworkPolicy allowing ingress on port 3306 only from the WordPress and
bootstrap pods.

## Local domain approach

For Minikube on Windows, enable the ingress-nginx addon:

```powershell
minikube addons enable ingress
minikube tunnel
```

The local overlay uses `shop.localhost`. Modern browsers resolve
`*.localhost` to `127.0.0.1`, so no hosts-file entry is normally required.
Open `http://shop.localhost` after the ingress controller and chart are ready.
If the local browser or ingress setup does not resolve the wildcard, use the
Minikube IP and add a hosts entry for `shop.localhost`.

## Secrets

No passwords or WooCommerce keys are committed in the chart. Use a Kubernetes
Secret with the key names configured in `values.yaml`:

```powershell
kubectl create namespace store
kubectl -n store create secret generic store-secrets `
  --from-literal=mariadb-root-password='replace-me' `
  --from-literal=mariadb-password='replace-me' `
  --from-literal=wordpress-admin-password='replace-me'
```

Then install with `--set secrets.existingSecret=store-secrets`. The
post-install hook generates the WooCommerce REST `read_write` key and secret
and patches those two keys into the same Secret. To supply all values directly
instead, use `--set-string` flags or a local, gitignored
`values-secrets.yaml`; never commit that file.

If `existingSecret` is empty, the chart-created Secret generates stable
passwords using `lookup` on upgrades. The chart values contain empty strings,
not credentials.

## Install on Minikube

```powershell
helm upgrade --install store .\charts\store `
  --namespace store --create-namespace `
  -f .\charts\store\values-local.yaml `
  --set-string secrets.mariadbRootPassword='replace-me' `
  --set-string secrets.mariadbPassword='replace-me' `
  --set-string secrets.wordpressAdminPassword='replace-me'
```

Or use a local ignored file:

```powershell
@'
secrets:
  mariadbRootPassword: replace-me
  mariadbPassword: replace-me
  wordpressAdminPassword: replace-me
'@ | Set-Content .\charts\store\values-secrets.yaml

helm upgrade --install store .\charts\store `
  --namespace store --create-namespace `
  -f .\charts\store\values-local.yaml `
  -f .\charts\store\values-secrets.yaml
```

The generated REST credentials are stored in the Secret named by
`secrets.existingSecret`, or in `<release>-store` when that value is empty.

## Install on k3s

Use the same chart and only change values:

```powershell
helm upgrade --install store .\charts\store `
  --namespace store --create-namespace `
  -f .\charts\store\values-prod.yaml `
  -f .\charts\store\values-secrets.yaml `
  --set secrets.existingSecret=store-secrets
```

Set the production hostname, storage class, and optional `ingress.tls` block
in a deployment-specific values file. Do not expose the MariaDB Service through
an Ingress or NodePort.

## Manual test list

1. Run `helm lint charts/store`.
2. Render both overlays with `helm template` and confirm the images are pinned,
   no Secret data contains committed credentials, and the database Service is
   ClusterIP.
3. Install into Minikube and wait for the MariaDB and WordPress pods.
4. Confirm the bootstrap Job completes and the sample pages exist.
5. Open `http://shop.localhost/wp-login.php` and log in with the supplied admin
   credentials.
6. Visit `/wp-json` and confirm pretty permalinks are active.
7. Confirm WooCommerce is active and Cash on Delivery is enabled.
8. Read the generated REST key Secret and make a harmless WooCommerce REST
   request using the generated credentials.
9. Confirm an unrelated pod cannot connect to MariaDB:3306 while WordPress can.
10. Upgrade the release and confirm passwords remain unchanged and bootstrap is
    safe to re-run.
11. Repeat with `values-prod.yaml` and a real secret/domain in a k3s test
    namespace.

