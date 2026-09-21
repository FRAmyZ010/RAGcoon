import { clearClientAuth, getAuthToken, setAuthToken } from "./documentsApi";

const AUTH_BASE = "/api/v1/auth";

export { getAuthToken, setAuthToken };

export function isAuthenticated() {
  return Boolean(getAuthToken());
}

export function clearAuth() {
  clearClientAuth();
}

export async function login(username, password) {
  const res = await fetch(`${AUTH_BASE}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  let data = null;
  try {
    data = await res.json();
  } catch {
    // ignore
  }

  if (!res.ok) {
    const detail = data?.detail;
    const message =
      typeof detail === "string"
        ? detail
        : detail
          ? JSON.stringify(detail)
          : `Login failed (${res.status})`;
    const error = new Error(message);
    error.status = res.status;
    throw error;
  }

  if (!data?.access_token) {
    throw new Error("ไม่ได้รับ access_token จากเซิร์ฟเวอร์");
  }

  setAuthToken(data.access_token);
  if (data.username) localStorage.setItem("username", data.username);
  if (data.role) localStorage.setItem("role", data.role);
  return data;
}

export async function fetchMe() {
  const token = getAuthToken();
  if (!token) {
    throw new Error("ยังไม่ได้เข้าสู่ระบบ");
  }

  const res = await fetch(`${AUTH_BASE}/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) {
    if (res.status === 401) {
      clearClientAuth();
      if (!window.location.pathname.startsWith("/login")) {
        window.location.assign("/login");
      }
    }
    let detail = `Failed to load profile (${res.status})`;
    try {
      const data = await res.json();
      if (data?.detail) {
        detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      }
    } catch {
      // keep
    }
    const error = new Error(detail);
    error.status = res.status;
    throw error;
  }

  return res.json();
}
