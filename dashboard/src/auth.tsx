import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { Navigate, Outlet, useLocation, useNavigate } from "react-router-dom";
import { api, setUnauthorizedHandler } from "./lib/api";
import { Role, User } from "./types";

type AuthContextValue = { user: User | null; loading: boolean; login: (email: string, password: string) => Promise<void>; logout: () => Promise<void>; refresh: () => Promise<void> };
const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const refresh = async () => {
    if (!sessionStorage.getItem("mcp_session")) { setUser(null); return; }
    setUser(await api<User>("/auth/me"));
  };
  useEffect(() => {
    setUnauthorizedHandler(() => { setUser(null); navigate("/login", { replace: true }); });
    refresh().catch(() => setUser(null)).finally(() => setLoading(false));
  }, []);
  const value = useMemo<AuthContextValue>(() => ({
    user, loading,
    login: async (email, password) => {
      const result = await api<{ access_token: string }>("/auth/login", { method: "POST", json: { email, password } });
      sessionStorage.setItem("mcp_session", result.access_token);
      await refresh();
    },
    logout: async () => {
      try { await api("/auth/logout", { method: "POST" }); } finally { sessionStorage.removeItem("mcp_session"); setUser(null); navigate("/login"); }
    },
    refresh,
  }), [user, loading]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
export function useAuth() { const value = useContext(AuthContext); if (!value) throw new Error("AuthProvider missing"); return value; }
export function RequireAuth() { const { user, loading } = useAuth(); const location = useLocation(); if (loading) return <div className="p-10 text-muted-foreground">Loading…</div>; return user ? <Outlet /> : <Navigate to="/login" replace state={{ from: location }} />; }
export function RequireAdmin() { const { user } = useAuth(); return user?.role === ("admin" satisfies Role) ? <Outlet /> : <div className="p-10"><h1 className="text-2xl font-semibold">Not allowed</h1><p className="mt-2 text-muted-foreground">You do not have access to this page.</p></div>; }
