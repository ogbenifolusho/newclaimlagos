export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("claim_token");
}

export function getUser(): { id: string; email: string; full_name: string; roles: string[] } | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem("claim_user");
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function logout() {
  localStorage.removeItem("claim_token");
  localStorage.removeItem("claim_user");
  window.location.href = "/login";
}

export function authHeaders(): HeadersInit {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export function hasRole(role: string): boolean {
  const user = getUser();
  return !!user?.roles?.includes(role) || !!user?.roles?.includes("super_admin");
}
