export class ApiError extends Error {
  status: number;
  detail: string;
  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

export function formatApiErrorDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .filter((item): item is { loc: unknown; msg: unknown } =>
        typeof item === "object" && item !== null &&
        "loc" in item && "msg" in item
      )
      .map(item => {
        const location = Array.isArray(item.loc)
          ? item.loc.join(".")
          : String(item.loc);
        return `${location}: ${String(item.msg)}`;
      });
    if (messages.length) return messages.join("\n");
  }
  return "Request failed";
}

let onUnauthorized: (() => void) | undefined;
export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler;
}

export async function api<T>(
  path: string,
  options: RequestInit & { json?: unknown } = {},
): Promise<T> {
  const token = sessionStorage.getItem("mcp_session");
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");
  if (options.json !== undefined) {
    headers.set("Content-Type", "application/json");
  }
  if (token) headers.set("Authorization", "Bearer " + token);
  const requestPath = path.startsWith("/") ? `/api${path}` : `/api/${path}`;
  const response = await fetch(requestPath, {
    ...options,
    headers,
    body: options.json === undefined ? options.body : JSON.stringify(options.json),
  });
  const raw = await response.text();
  let data: unknown = {};
  try { data = raw ? JSON.parse(raw) : {}; } catch { data = { detail: raw }; }
  if (!response.ok) {
    const detail = typeof data === "object" && data !== null && "detail" in data
      ? formatApiErrorDetail((data as { detail: unknown }).detail)
      : `Request failed with status ${response.status}`;
    if (response.status === 401) {
      sessionStorage.removeItem("mcp_session");
      onUnauthorized?.();
    }
    throw new ApiError(response.status, detail);
  }
  return data as T;
}
