# MCP Gateway Dashboard

This is a separate Vite + React + TypeScript microservice. It connects to the
gateway through relative browser requests; Vite proxies those requests during
development.

## Run locally

```powershell
cd C:\woo-mcp-lab\dashboard
npm install
npm run dev
```

The dashboard is served at `http://127.0.0.1:3000`.

Environment variables:

- `GATEWAY_PROXY_TARGET` - gateway origin used by the Vite proxy. Defaults to
  `http://127.0.0.1:9000`.
- `VITE_GATEWAY_URL` is used for the copyable MCP client URL. The dashboard
  calls the gateway through the `/api` prefix; Vite strips that prefix during
  development and nginx does so in the container.
- Gateway `DASHBOARD_BASE_URL` should be
  `http://127.0.0.1:3000` so generated invitations point to this service.
All authenticated dashboard requests use a bearer Authorization header.
Session tokens are stored only in sessionStorage. The client

redirects to `/login` and clears the token on HTTP 401. Error responses use
FastAPI's `{ "detail": string }` shape.

| Endpoint | Request | Response |
| --- | --- | --- |
| `POST /auth/login` | `{ email, password }` | `{ access_token, token_type, expires_at }` |
| `GET /auth/me` | none | `{ id, email, display_name, role }` |
| `POST /auth/logout` | none | `{ logged_out: true }` |
| `POST /auth/invitations` | `{ email, role }` | `{ id, invite_url, expires_at }` |
| `GET /auth/invitations` | none | `{ invitations: [{ id, email, role, expires_at, accepted_at, revoked_at, created_at }] }` |
| `DELETE /auth/invitations/{id}` | none | `{ revoked: true }` |
| `POST /auth/invitations/accept` | `{ token, password, display_name }` | `{ user_id }` |
| `POST /auth/api-keys` | `{ name, expires_at }` | `{ id, key, name }`; `key` is returned once |
| `GET /auth/api-keys` | none | `{ keys: [{ id, name, key_prefix, created_at, last_used_at, expires_at, revoked_at }] }` |
| `DELETE /auth/api-keys/{id}` | none | `{ revoked: true }` |
| `GET /admin/api-keys` | none | `{ keys: [{ id, user_id, owner_email, name, key_prefix, created_at, last_used_at, expires_at, revoked_at }] }` |
| `DELETE /admin/api-keys/{id}` | none | `{ revoked: true }` |
| `GET /admin/users` | none | `{ users: [{ id, email, display_name, role, is_active, created_at, last_login_at }] }` |
| `PATCH /admin/users/{id}` | `{ role?, is_active? }` | `{ id, email, role, is_active }` |
| `GET /admin/servers` | none | `{ servers: [{ id, name, url, description, enabled, status, request_timeout_seconds, max_concurrent_requests, last_checked_at, last_error, has_credential, tool_count }] }` |
| `POST /admin/servers` | `{ id, name, url, description, enabled?, request_timeout_seconds?, max_concurrent_requests?, credential? }` | One server object as above |
| `PATCH /admin/servers/{id}` | Any editable server fields; credential is write-only | One server object as above |
| `POST /admin/servers/{id}/enable` / `disable` | none | One server object as above |
| `POST /admin/servers/{id}/sync` | none | `{ tools: [...] }` |
| `GET /admin/servers/{id}/tools` | none | `{ tools: [{ id, name, original_name, description, input_schema, enabled, deprecated }] }` |
| `DELETE /admin/servers/{id}` | none | `{ deleted: true }` |
| `GET /tools/available` | none | `{ tools: [{ id, name, original_name, description, input_schema, enabled, deprecated }] }` |
| `GET /admin/permissions` | none | `{ permissions: [{ id, tool_id, user_id, role, allowed }] }` |
| `POST /admin/permissions` | `{ tool_id, allowed, user_id? | role? }` | `{ id, allowed }` |
| `GET /admin/audit` | `user_id?, server?, tool?, outcome?, from_date?, to_date?, limit?, offset?` | `{ items: [{ user_id, user_email, server, tool, time, duration_ms, outcome }], limit, offset, total }` |
| `GET /audit` | `server?, tool?, outcome?, from_date?, to_date?, limit?, offset?` | Same audit response, restricted to the current user |

The gateway additions required by the dashboard are `GET /auth/me`, server
`tool_count`, API-key `last_used_at` and admin `owner_email`, and audit
`from_date`, `to_date`, `total`, and `user_email`. No password hashes, token
hashes, raw API keys except at creation, or upstream credentials are returned.

## Manual test list

1. Set `VITE_GATEWAY_URL`, start the gateway, then run the dashboard.
2. Log in as admin and confirm the browser stores only the session token in
   session storage.
3. Refresh the page and confirm `/auth/me` restores the user.
4. Log in as a member and confirm admin routes show **Not allowed**.
5. Accept an invitation, confirm display name/password validation, then log in.
6. Create an API key, copy the raw key, close the modal, and confirm it is no
   longer visible in the UI.
7. Create/edit/disable/sync/delete a server; verify credential values are never
   prefilled or displayed.
8. Change member role and active state; invite and revoke an invitation.
9. Exercise audit filters and pagination.
10. Toggle role permissions and verify Tools changes.
11. Confirm the Chat page is explicitly a placeholder.

## Progress

| Page | Status | Known gaps |
| --- | --- | --- |
| Login | Built | None known |
| Accept invitation | Built | None known |
| Layout and guards | Built | Mobile navigation is intentionally minimal |
| Servers | Built | Toasts use a lightweight browser event and need a richer toast provider later |
| My API Keys | Built | Snippet text is intentionally generic |
| Members | Built | Invitation list currently displays all historical rows from the API |
| Audit Log | Built | Date filter is sent as local datetime |
| Tools | Built | Grouping derives server ID from public tool name |
| Permissions | Built | Matrix lists currently available tools |
| Chat | Placeholder | Backend/chat UX not implemented by request |
