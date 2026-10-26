export type Role = "admin" | "member";
export type User = { id: string; email: string; display_name: string | null; role: Role };
export type Server = {
  id: string; name: string; url: string; description: string; enabled: boolean;
  status: "Connected" | "Unreachable" | "Checking" | "Disabled"; request_timeout_seconds: number;
  max_concurrent_requests: number; last_checked_at: string | null; last_error: string | null;
  has_credential: boolean; tool_count: number;
};
export type Tool = { id: number; name: string; original_name: string; description: string; input_schema: Record<string, unknown>; enabled: boolean; deprecated: boolean; server_id?: string };
export type ApiKey = { id: string; user_id?: string; owner_email?: string; name: string; key_prefix: string; created_at: string; last_used_at?: string | null; expires_at: string | null; revoked_at: string | null };
export type Permission = { id: number; tool_id: number; user_id: string | null; role: Role | null; allowed: boolean };
export type AuditItem = { user_id: string | null; user_email?: string | null; server: string | null; tool: string | null; time: string; duration_ms: number | null; outcome: string };
