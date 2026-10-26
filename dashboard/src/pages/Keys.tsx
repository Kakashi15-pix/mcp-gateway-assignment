import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { ApiKey } from "../types";
import { Button, Card, Empty, ErrorState, Input, Loading, Modal, PageHeader } from "../components/ui";
import { formatDate } from "../lib/utils";
import { useAuth } from "../auth";

function Copy({ value }: { value: string }) {
  return <Button variant="secondary" onClick={() => void navigator.clipboard.writeText(value)}>Copy</Button>;
}

export function Keys() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const [create, setCreate] = useState(false);
  const [raw, setRaw] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [expires_at, setExpires] = useState("");
  const [showRevoked, setShowRevoked] = useState(false);
  const isAdmin = user?.role === "admin";
  const mine = useQuery({
    queryKey: ["keys"],
    queryFn: () => api<{ keys: ApiKey[] }>("/auth/api-keys"),
  });
  const all = useQuery({
    queryKey: ["all-keys"],
    queryFn: () => api<{ keys: ApiKey[] }>("/admin/api-keys"),
    enabled: isAdmin,
  });

  async function createKey() {
    const result = await api<{ key: string }>("/auth/api-keys", {
      method: "POST",
      json: { name, expires_at: expires_at || null },
    });
    setCreate(false);
    setName("");
    setExpires("");
    setRaw(result.key);
    await qc.invalidateQueries({ queryKey: ["keys"] });
  }

  async function revoke(id: string, admin = false) {
    if (!confirm("Revoke this API key?")) return;
    await api(`${admin ? "/admin" : "/auth"}/api-keys/${id}`, { method: "DELETE" });
    await qc.invalidateQueries({ queryKey: [admin ? "all-keys" : "keys"] });
  }

  const loading = mine.isLoading || (isAdmin && all.isLoading);
  if (loading) return <Loading />;
  if (mine.isError || (isAdmin && all.isError)) {
    return <ErrorState error={mine.error || all.error} />;
  }

  const rows = isAdmin ? all.data?.keys || [] : mine.data!.keys;
  const statusFor = (key: ApiKey) => {
    if (key.revoked_at) return "Revoked";
    if (key.expires_at && new Date(key.expires_at).getTime() < Date.now()) {
      return "Expired";
    }
    return "Active";
  };
  const visibleRows = rows
    .filter(key => showRevoked || statusFor(key) !== "Revoked")
    .sort((a, b) => {
      const order = { Active: 0, Expired: 1, Revoked: 2 };
      return order[statusFor(a) as keyof typeof order]
        - order[statusFor(b) as keyof typeof order];
    });
  const gatewayUrl = import.meta.env.VITE_GATEWAY_URL || `${window.location.origin}/mcp`;
  const snippets = [
    {
      label: "MCP Inspector",
      value: [
        "npx @modelcontextprotocol/inspector",
        "",
        "Transport: Streamable HTTP",
        `URL: ${gatewayUrl}`,
        "Add header: Authorization = Bearer mcp_YOUR_KEY",
      ].join("\n"),
    },
    {
      label: "Claude Code",
      value: `claude mcp add --transport http gateway ${gatewayUrl} --header "Authorization: Bearer mcp_YOUR_KEY"`,
    },
    {
      label: "Cursor (.cursor/mcp.json)",
      value: `{
  "mcpServers": {
    "gateway": {
      "url": "${gatewayUrl}",
      "headers": { "Authorization": "Bearer mcp_YOUR_KEY" }
    }
  }
}`,
    },
  ];
  return <>
    <PageHeader title="My API Keys" description="Manage client credentials. Raw keys are shown only once." action={<Button onClick={() => setCreate(true)}>Create key</Button>} />
    <Card>
      <div className="mb-4 flex justify-end">
        <label className="flex items-center gap-2 text-sm text-muted-foreground">
          <input type="checkbox" checked={showRevoked} onChange={e => setShowRevoked(e.target.checked)} />
          Show revoked
        </label>
      </div>
      <div>
        <table className="w-full table-fixed text-left text-xs sm:text-sm">
          <thead className="text-muted-foreground"><tr><th className="w-[22%] p-2 sm:p-3">Name</th>{isAdmin && <th className="w-[20%] p-2 sm:p-3">Owner</th>}<th className="w-[15%] p-2 sm:p-3">Prefix</th><th className="w-[15%] p-2 sm:p-3">Created</th><th className="w-[15%] p-2 sm:p-3">Expires</th><th className="w-[13%] p-2 sm:p-3">Status</th><th className="w-[10%] p-2 sm:p-3" /></tr></thead>
          <tbody>{visibleRows.map(k => {
            const status = statusFor(k);
            return <tr className="border-t border-border" key={k.id}><td className="truncate p-2 sm:p-3">{k.name}</td>{isAdmin && <td className="truncate p-2 sm:p-3">{k.owner_email || user?.email}</td>}<td className="truncate p-2 font-mono sm:p-3">{k.key_prefix}…</td><td className="p-2 sm:p-3">{formatDate(k.created_at)}</td><td className="p-2 sm:p-3">{formatDate(k.expires_at)}</td><td className="p-2 sm:p-3"><span className={status === "Active" ? "text-emerald-300" : status === "Revoked" ? "text-red-300" : "text-muted-foreground"}>{status}</span></td><td className="p-2 text-right sm:p-3">{status === "Active" && <Button variant="danger" onClick={() => void revoke(k.id, isAdmin)}>Revoke</Button>}</td></tr>;
          })}</tbody>
        </table>
        {!visibleRows.length && <Empty>{rows.length ? "No keys to show." : "No API keys yet."} <Button className="mt-3" onClick={() => setCreate(true)}>Create key</Button></Empty>}
      </div>
    </Card>
    <Card className="mt-5">
      <h2 className="font-semibold">Connect a client</h2>
      <p className="mt-2 text-sm text-muted-foreground">Gateway URL</p>
      <code className="mt-1 block rounded bg-black/30 p-3 text-sm">{gatewayUrl}</code>
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        {snippets.map(({ label, value }) => <div className="rounded-lg border border-border p-3" key={label}>
          <p className="font-medium">{label}</p>
          <pre className="my-2 overflow-x-auto whitespace-pre-wrap rounded bg-black/30 p-3 text-xs text-muted-foreground">{value}</pre>
          <Copy value={value} />
        </div>)}
      </div>
    </Card>
    {create && <Modal title="Create API key" onClose={() => setCreate(false)}><div className="space-y-4"><label className="block text-sm">Name<Input className="mt-1" value={name} onChange={e => setName(e.target.value)} required /></label><label className="block text-sm">Expiry (optional)<Input className="mt-1" type="datetime-local" value={expires_at} onChange={e => setExpires(e.target.value)} /></label><Button disabled={!name} onClick={() => void createKey()}>Create</Button></div></Modal>}
    {raw && <Modal title="Copy your API key" onClose={() => setRaw(null)}><p className="text-sm text-amber-200">This key will not be shown again. Store it securely.</p><code className="my-4 block break-all rounded bg-black/30 p-3">{raw}</code><Copy value={raw} /></Modal>}
  </>;
}
