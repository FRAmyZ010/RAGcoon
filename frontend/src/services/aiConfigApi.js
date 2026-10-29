import { clearClientAuth, getAuthToken } from "./documentsApi";

const BASE = "/api/v1/config";

function authHeaders(extra = {}) {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}`, ...extra } : extra;
}

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: authHeaders(options.body ? { "Content-Type": "application/json" } : {}),
  });
  if (res.status === 401) {
    clearClientAuth();
    if (!window.location.pathname.startsWith("/login")) window.location.assign("/login");
  }
  if (!res.ok) {
    let detail = "Request failed";
    try {
      const data = await res.json();
      if (typeof data?.detail === "string") detail = data.detail;
    } catch {
      // keep
    }
    throw new Error(detail);
  }
  return res.json();
}

export const fetchIntents = () => request("/intents");
export const saveIntent = (name, payload) =>
  request(`/intents/${name}`, { method: "PUT", body: JSON.stringify(payload) });
export const resetIntents = () => request("/intents/reset", { method: "POST" });
export const fetchRag = () => request("/rag");
export const applyPreset = (name) => request(`/rag/preset/${encodeURIComponent(name)}`, { method: "POST" });
export const saveRagProfile = (payload) =>
  request("/rag/profiles", { method: "POST", body: JSON.stringify(payload) });
export const saveNamedPreset = (payload) =>
  request("/presets", { method: "POST", body: JSON.stringify(payload) });
export const deleteNamedPreset = (name) =>
  request(`/presets/${encodeURIComponent(name)}`, { method: "DELETE" });
export const rankQuality = (presetNames) =>
  request("/benchmark/quality", {
    method: "POST",
    body: JSON.stringify({ limit: 8, repeats: 5, preset_names: presetNames }),
  });
export const fetchLlms = () => request("/llms");
export const setActiveLlm = (provider, model) =>
  request("/llms/set-active", { method: "POST", body: JSON.stringify({ provider, model }) });
export const pingLlm = (provider, model) =>
  request("/llms/test-connectivity", { method: "POST", body: JSON.stringify({ provider, model }) });
export const runBenchmark = (baseline, candidate) =>
  request("/benchmark/run", {
    method: "POST",
    body: JSON.stringify({ baseline, candidate, limit: 8, repeats: 5 }),
  });
