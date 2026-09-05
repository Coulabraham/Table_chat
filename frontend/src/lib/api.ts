function apiBaseUrl() {
  if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL;
  if (typeof window !== "undefined") return `${window.location.protocol}//${window.location.hostname}:8000/api`;
  return "http://localhost:8000/api";
}

function cookie(name: string) {
  if (typeof document === "undefined") return "";
  return document.cookie.split("; ").find((item) => item.startsWith(`${name}=`))?.split("=")[1] ?? "";
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body) headers.set("Content-Type", "application/json");
  const csrf = cookie("csrftoken");
  if (csrf) headers.set("X-CSRFToken", decodeURIComponent(csrf));
  const response = await fetch(`${apiBaseUrl()}${path}`, { ...options, headers, credentials: "include" });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.detail ?? Object.values(payload ?? {})[0] ?? "Une erreur est survenue.");
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

export async function ensureCsrf() {
  return api<{ csrfToken: string }>("/auth/csrf/");
}

export function wsUrl(path: string) {
  if (process.env.NEXT_PUBLIC_WS_URL) return `${process.env.NEXT_PUBLIC_WS_URL}${path}`;
  if (typeof window !== "undefined") {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${protocol}//${window.location.hostname}:8000/ws${path}`;
  }
  return `ws://localhost:8000/ws${path}`;
}
