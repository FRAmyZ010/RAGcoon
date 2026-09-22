const DOCUMENTS_BASE = "/api/v1/documents";
export const MAX_UPLOAD_BYTES = 25 * 1024 * 1024;
export const MAX_TOTAL_UPLOAD_BYTES = 10 * 1024 * 1024;
export const MAX_BATCH_UPLOAD_FILES = 10;
export const MAX_UPLOAD_MB = MAX_UPLOAD_BYTES / (1024 * 1024);
export const MAX_TOTAL_UPLOAD_MB = MAX_TOTAL_UPLOAD_BYTES / (1024 * 1024);
const AUTH_TOKEN_KEY = "token";

export function getAuthToken() {
  return localStorage.getItem(AUTH_TOKEN_KEY);
}

export function setAuthToken(token) {
  if (!token) {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    return;
  }
  localStorage.setItem(AUTH_TOKEN_KEY, token);
}

/** Clear token + cached profile fields (no navigation). */
export function clearClientAuth() {
  setAuthToken(null);
  localStorage.removeItem("username");
  localStorage.removeItem("role");
}

function redirectToLoginIfUnauthorized(status) {
  if (status !== 401) return;
  clearClientAuth();
  if (!window.location.pathname.startsWith("/login")) {
    window.location.assign("/login");
  }
}

function authHeaders(extra = {}) {
  const token = getAuthToken();
  if (!token) return { ...extra };
  return {
    ...extra,
    Authorization: `Bearer ${token}`,
  };
}

async function parseErrorDetail(res, fallback) {
  let detail = fallback;
  try {
    const data = await res.json();
    if (data?.detail) {
      detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
    }
  } catch {
    // keep fallback
  }
  const error = new Error(detail);
  error.status = res.status;
  return error;
}

async function rejectIfNotOk(res, fallback) {
  if (res.ok) return;
  redirectToLoginIfUnauthorized(res.status);
  throw await parseErrorDetail(res, fallback);
}

export async function listDocuments() {
  const res = await fetch(DOCUMENTS_BASE, {
    headers: authHeaders(),
  });
  await rejectIfNotOk(res, `Failed to load documents (${res.status})`);
  return res.json();
}

export async function uploadDocument(file, options = {}) {
  if (!file) {
    throw new Error("ไม่ได้เลือกไฟล์");
  }
  if (!file.name?.toLowerCase().endsWith(".pdf")) {
    throw new Error("รองรับเฉพาะไฟล์เอกสารประเภท PDF เท่านั้น");
  }
  if (file.size <= 0) {
    throw new Error("ไฟล์ว่างเปล่า ไม่สามารถอัปโหลดได้");
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    throw new Error(`ไฟล์ใหญ่เกิน ${MAX_UPLOAD_MB}MB`);
  }

  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${DOCUMENTS_BASE}/upload`, {
    method: "POST",
    headers: authHeaders(),
    body: formData,
    signal: options.signal,
  });

  await rejectIfNotOk(res, `Upload failed (${res.status})`);
  return res.json();
}

/**
 * Upload up to MAX_BATCH_UPLOAD_FILES PDFs. Returns { results, summary }.
 * Partial success is normal (HTTP 200 with failed items in results).
 */
export async function uploadDocumentsBatch(files) {
  const list = Array.from(files || []);
  if (list.length === 0) {
    throw new Error("ไม่ได้เลือกไฟล์");
  }
  if (list.length > MAX_BATCH_UPLOAD_FILES) {
    throw new Error(`อัปโหลดได้สูงสุด ${MAX_BATCH_UPLOAD_FILES} ไฟล์ต่อครั้ง`);
  }

  const totalBytes = list.reduce((sum, file) => sum + (file.size || 0), 0);
  if (totalBytes > MAX_TOTAL_UPLOAD_BYTES) {
    throw new Error(`ขนาดไฟล์รวมเกิน ${MAX_TOTAL_UPLOAD_MB}MB`);
  }

  for (const file of list) {
    if (!file.name?.toLowerCase().endsWith(".pdf")) {
      throw new Error(`รองรับเฉพาะไฟล์ PDF เท่านั้น: ${file.name}`);
    }
    if (file.size <= 0) {
      throw new Error(`ไฟล์ว่างเปล่า ไม่สามารถอัปโหลดได้: ${file.name}`);
    }
    if (file.size > MAX_UPLOAD_BYTES) {
      throw new Error(`ไฟล์ใหญ่เกิน ${MAX_UPLOAD_MB}MB: ${file.name}`);
    }
  }

  const formData = new FormData();
  for (const file of list) {
    formData.append("files", file);
  }

  const res = await fetch(`${DOCUMENTS_BASE}/upload-batch`, {
    method: "POST",
    headers: authHeaders(),
    body: formData,
  });

  await rejectIfNotOk(res, `Batch upload failed (${res.status})`);
  return res.json();
}

export async function deleteDocument(documentId) {
  const res = await fetch(`${DOCUMENTS_BASE}/${documentId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });

  await rejectIfNotOk(res, `Delete failed (${res.status})`);
  return res.json();
}

/** Open PDF preview in a new browser tab (optionally jump to page). */
export function openDocumentPreview(documentId, page) {
  if (!documentId) return;
  const pageNum = page && Number(page) > 0 ? Number(page) : null;
  const url = pageNum
    ? `${DOCUMENTS_BASE}/${documentId}/file#page=${pageNum}`
    : `${DOCUMENTS_BASE}/${documentId}/file`;
  window.open(url, "_blank", "noopener,noreferrer");
}

export function getDocumentFileUrl(documentId) {
  if (!documentId) return null;
  return `${DOCUMENTS_BASE}/${documentId}/file`;
}

export function mapDocumentToRow(doc) {
  const statusMap = {
    COMPLETED: "Ready",
    PROCESSING: "Processing",
    PENDING: "Processing",
    FAILED: "Failed",
  };

  const uploadDate = doc.upload_date ? new Date(doc.upload_date) : null;

  return {
    id: doc.id,
    title: doc.title || doc.filename || "Untitled",
    filename: doc.filename,
    source: doc.filename || "—",
    authors: doc.authors || "—",
    advisor: doc.advisor || "—",
    year: doc.academic_year != null ? String(doc.academic_year) : "—",
    keywords: doc.keywords || "—",
    supervisoryCommittee: doc.supervisory_committee || "—",
    status: statusMap[doc.status] || doc.status || "Processing",
    date: uploadDate
      ? uploadDate.toLocaleDateString("en-GB", {
          day: "2-digit",
          month: "short",
          year: "numeric",
        })
      : "—",
  };
}
