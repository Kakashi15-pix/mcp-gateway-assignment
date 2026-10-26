import { Link, NavLink, Outlet } from "react-router-dom";
import { Activity, Boxes, ClipboardList, KeyRound, MessageSquare, Network, ShieldCheck, Users, LogOut } from "lucide-react";
import { useAuth } from "./auth";
import { cn } from "./lib/utils";
import { Button } from "./components/ui";

const common = [{ to: "/tools", label: "Tools", icon: Boxes }, { to: "/keys", label: "My API Keys", icon: KeyRound }, { to: "/chat", label: "Chat", icon: MessageSquare }];
const admin = [{ to: "/servers", label: "Servers", icon: Network }, { to: "/members", label: "Members", icon: Users }, { to: "/permissions", label: "Permissions", icon: ShieldCheck }, { to: "/audit", label: "Audit Log", icon: ClipboardList }];
export function Layout() {
  const { user, logout } = useAuth();
  const items = user?.role === "admin" ? [...admin, ...common] : common;
  return <div className="flex min-h-screen bg-background">
    <aside className="hidden w-64 shrink-0 border-r border-border bg-card p-4 md:block"><Link to="/" className="mb-8 flex items-center gap-2 px-3 text-lg font-semibold"><Activity className="text-primary" /> MCP Gateway</Link><nav className="space-y-1">{items.map(({ to, label, icon: Icon }) => <NavLink key={to} to={to} className={({ isActive }) => cn("flex items-center gap-3 rounded-lg px-3 py-2 text-sm", isActive ? "bg-primary/15 text-primary" : "text-muted-foreground hover:bg-muted hover:text-foreground")}><Icon size={17} />{label}</NavLink>)}</nav></aside>
    <main className="min-w-0 flex-1"><header className="flex min-h-16 items-center justify-between border-b border-border px-4 md:px-8"><div className="md:hidden"><Link to="/" className="font-semibold">MCP Gateway</Link></div><div className="ml-auto flex items-center gap-4 text-sm"><span className="text-muted-foreground">{user?.email}</span><Button variant="ghost" onClick={() => void logout()}><LogOut size={16} className="mr-2" />Logout</Button></div></header><div className="mx-auto max-w-7xl p-4 md:p-8"><Outlet /></div></main>
  </div>;
}
