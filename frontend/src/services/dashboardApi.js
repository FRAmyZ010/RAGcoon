import { clearClientAuth, getAuthToken } from "./documentsApi";

const DASHBOARD_BASE = "/api/v1/dashboard";

export async function fetchOverview() {
  const token = getAuthToken();
  const res = await fetch(`${DASHBOARD_BASE}/overview`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  if (res.status === 401) {
    clearClientAuth();
    if (!window.location.pathname.startsWith("/login")) {
      window.location.assign("/login");
    }
  }

  if (!res.ok) {
    let detail = "โหลด Dashboard ไม่สำเร็จ";
    try {
      const data = await res.json();
      if (typeof data?.detail === "string") detail = data.detail;
    } catch {
      // keep
    }
    const error = new Error(detail);
    error.status = res.status;
    throw error;
  }

  return res.json();
}
