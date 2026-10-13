const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchOverview() {
  const res = await fetch(`${API_BASE}/api/v1/situation-room/overview`, {
    next: { revalidate: 30 },
  });
  if (!res.ok) throw new Error("Failed to load Situation Room overview");
  return res.json();
}

export async function fetchGeoHierarchy(level?: string) {
  const url = level
    ? `${API_BASE}/api/v1/geo/hierarchy?level=${level}`
    : `${API_BASE}/api/v1/geo/hierarchy`;
  const res = await fetch(url);
  if (!res.ok) throw new Error("Failed to load geo hierarchy");
  return res.json();
}

export async function login(email: string, password: string) {
  const body = new URLSearchParams();
  body.append("username", email);
  body.append("password", password);
  const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!res.ok) throw new Error("Login failed");
  return res.json();
}
