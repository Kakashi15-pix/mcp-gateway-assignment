import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { Tool } from "../types";
import { Card, Empty, ErrorState, Loading, PageHeader } from "../components/ui";
export function Tools() {
  const query = useQuery({ queryKey: ["tools"], queryFn: () => api<{ tools: Tool[] }>("/tools/available"), staleTime: 0, refetchOnWindowFocus: true, refetchInterval: 15000 });
  if (query.isLoading) return <Loading />; if (query.isError) return <ErrorState error={query.error} retry={() => void query.refetch()} />;
  const data = query.data!;
  const grouped = data.tools.reduce<Record<string, Tool[]>>((a, t) => { const key = t.name.split("__")[0]; (a[key] ||= []).push(t); return a; }, {});
  return <><PageHeader title="Tools" description="Tools currently available to your account." />{!data.tools.length ? <Empty /> : <div className="grid gap-4 md:grid-cols-2">{Object.entries(grouped).map(([server, tools]) => <Card key={server}><h2 className="font-semibold">{server}</h2><div className="mt-4 space-y-3">{tools.map(t => <div key={t.id} className="rounded-lg border border-border p-3"><p className="font-medium">{t.original_name}</p><p className="mt-1 text-sm text-muted-foreground">{t.description || "No description."}</p></div>)}</div></Card>)}</div>}</>;
}
