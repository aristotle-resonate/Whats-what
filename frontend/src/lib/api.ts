import type { TrendingResponse } from "./types";

const BASE = "/api";

export async function fetchTrending(
  city: string,
  category?: string,
  limit = 20
): Promise<TrendingResponse> {
  const params = new URLSearchParams({ city, limit: String(limit) });
  if (category) params.set("category", category);

  const res = await fetch(`${BASE}/trending?${params}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Trending fetch failed: ${res.status}`);
  return res.json();
}

export async function requestMagicLink(email: string): Promise<void> {
  const res = await fetch(`${BASE}/auth/request-link`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  if (!res.ok) throw new Error("Failed to send sign-in link");
}

export async function verifyMagicToken(token: string): Promise<{
  access_token: string;
  user_id: number;
  onboarding_completed: boolean;
}> {
  const res = await fetch(`${BASE}/auth/verify?token=${encodeURIComponent(token)}`);
  if (!res.ok) throw new Error("Invalid or expired link");
  return res.json();
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("ww_token");
}

export function setToken(token: string): void {
  localStorage.setItem("ww_token", token);
}

export function clearToken(): void {
  localStorage.removeItem("ww_token");
}
