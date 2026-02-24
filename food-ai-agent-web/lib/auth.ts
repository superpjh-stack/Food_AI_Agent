const TOKEN_KEY = "food_ai_access_token";
const REFRESH_KEY = "food_ai_refresh_token";

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_KEY);
}

function setTokens(accessToken: string, refreshToken: string) {
  localStorage.setItem(TOKEN_KEY, accessToken);
  localStorage.setItem(REFRESH_KEY, refreshToken);
}

function clearTokens() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

export async function login(email: string, password: string) {
  const res = await fetch("/api/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    throw new Error("Login failed");
  }

  const data = await res.json();
  setTokens(data.access_token, data.refresh_token);
  return data;
}

export async function refreshAccessToken(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;

  try {
    const res = await fetch("/api/v1/auth/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!res.ok) {
      clearTokens();
      return false;
    }

    const data = await res.json();
    setTokens(data.access_token, data.refresh_token);
    return true;
  } catch {
    clearTokens();
    return false;
  }
}

export function logout() {
  clearTokens();
  window.location.href = "/login";
}
