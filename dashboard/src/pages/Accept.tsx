import { FormEvent, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../lib/api";
import { Button, Card, Input } from "../components/ui";
export function Accept() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const urlToken = params.get("token") || "";
  const [invitation, setInvitation] = useState(urlToken);
  const [display_name, setDisplay] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");

  function parseToken(value: string) {
    const input = value.trim();
    if (!input) return "";
    try {
      const url = new URL(input);
      return url.searchParams.get("token")?.trim() || "";
    } catch {
      return input;
    }
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    const token = parseToken(invitation);
    if (!token) {
      setError("Invitation link or token is required");
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match");
      return;
    }
    try {
      await api("/auth/invitations/accept", {
        method: "POST",
        json: { token, password, display_name: display_name || null },
      });
      navigate("/login", {
        replace: true,
        state: { toast: "Account created successfully. You can now sign in." },
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Invitation could not be accepted");
    }
  }

  return <div className="flex min-h-screen items-center justify-center p-4"><Card className="w-full max-w-md"><h1 className="text-2xl font-semibold">Accept invitation</h1><form onSubmit={submit} className="mt-6 space-y-4">{!urlToken && <label className="block text-sm">Invitation link or token<Input className="mt-1" value={invitation} onChange={e => setInvitation(e.target.value)} required placeholder="Paste an invite URL or token" /></label>}<label className="block text-sm">Display name<Input className="mt-1" value={display_name} onChange={e => setDisplay(e.target.value)} /></label><label className="block text-sm">Password<Input className="mt-1" type="password" minLength={12} value={password} onChange={e => setPassword(e.target.value)} required /><span className="mt-1 block text-xs text-muted-foreground">Must be at least 12 characters and at most 72 UTF-8 bytes.</span></label><label className="block text-sm">Confirm password<Input className="mt-1" type="password" minLength={12} value={confirm} onChange={e => setConfirm(e.target.value)} required /></label>{error && <p className="text-sm text-red-300">{error}</p>}<Button className="w-full" type="submit">Create account</Button><Link className="block text-center text-sm text-primary" to="/login">Back to sign in</Link></form></Card></div>;
}
