import { FormEvent, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Button, Card, Input } from "../components/ui";
import { useAuth } from "../auth";

export function Login() {
  const { login } = useAuth(); const navigate = useNavigate(); const location = useLocation();
  const [email, setEmail] = useState(""); const [password, setPassword] = useState(""); const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent) { event.preventDefault(); setBusy(true); setError(""); try { await login(email, password); navigate((location.state as { from?: { pathname: string } } | null)?.from?.pathname || "/"); } catch (e) { setError(e instanceof Error ? e.message : "Login failed"); } finally { setBusy(false); } }
  return <div className="flex min-h-screen items-center justify-center p-4"><Card className="w-full max-w-md"><h1 className="text-2xl font-semibold">Sign in</h1><p className="mt-1 text-sm text-muted-foreground">Access your MCP gateway dashboard.</p><form onSubmit={submit} className="mt-6 space-y-4"><label className="block text-sm">Email<Input className="mt-1" type="email" value={email} onChange={e => setEmail(e.target.value)} required /></label><label className="block text-sm">Password<Input className="mt-1" type="password" value={password} onChange={e => setPassword(e.target.value)} required /></label>{error && <p className="text-sm text-red-300">{error}</p>}<Button className="w-full" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</Button></form><p className="mt-5 text-center text-sm text-muted-foreground">Have an invitation? <Link className="text-primary hover:underline" to="/accept">Accept it</Link></p></Card></div>;
}
