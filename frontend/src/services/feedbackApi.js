import { getAuthToken } from "./documentsApi";

const FEEDBACK_BASE = "/api/v1/feedback";
export const MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024;

function authHeaders(extra = {}) {
  const token = getAuthToken();
  if (!token) return { ...extra };
  return { ...extra, Authorization: `Bearer ${token}` };
}

async function readError(response) {
  try {
    const data = await response.json();
    if (typeof data.detail === "string") return data.detail;
  } catch {
    /* ignore non-JSON errors */
  }
  return `Request failed (${response.status})`;
}

export async function submitFeedback(fields) {
  const body = new FormData();
  body.append("name", fields.name);
  body.append("rating", String(fields.rating));
  body.append("feedback_type", fields.feedbackType);
  body.append("comment", fields.comment);
  body.append("contact_gmail", fields.contactGmail ? "true" : "false");
  body.append("contact_phone", fields.contactPhone ? "true" : "false");
  if (fields.file) body.append("file", fields.file);
  if (fields.queryId) body.append("query_id", String(fields.queryId));

  const response = await fetch(FEEDBACK_BASE, { method: "POST", body });
  if (!response.ok) throw new Error(await readError(response));
  return response.json();
}

export async function listFeedback({ feedbackType = "All", status = "All", q = "" } = {}) {
  const params = new URLSearchParams();
  if (feedbackType && feedbackType !== "All") params.set("feedback_type", feedbackType);
  if (status && status !== "All") params.set("status", status);
  if (q.trim()) params.set("q", q.trim());
  const query = params.toString();
  const response = await fetch(`${FEEDBACK_BASE}${query ? `?${query}` : ""}`, {
    headers: authHeaders(),
  });
  if (!response.ok) throw new Error(await readError(response));
  return response.json();
}

export async function updateFeedbackStatus(id, status) {
  const response = await fetch(`${FEEDBACK_BASE}/${id}`, {
    method: "PATCH",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ status }),
  });
  if (!response.ok) throw new Error(await readError(response));
  return response.json();
}

export async function downloadFeedbackFile(id, filename) {
  const response = await fetch(`${FEEDBACK_BASE}/${id}/file`, {
    headers: authHeaders(),
  });
  if (!response.ok) throw new Error(await readError(response));
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename || `feedback-${id}`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
