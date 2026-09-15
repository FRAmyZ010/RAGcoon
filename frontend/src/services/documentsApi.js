const DOCUMENTS_BASE = "/api/v1/documents";

export async function listDocuments() {
  const res = await fetch(DOCUMENTS_BASE);
  if (!res.ok) {
    throw new Error(`Failed to load documents (${res.status})`);
  }
  return res.json();
}

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${DOCUMENTS_BASE}/upload`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    let detail = `Upload failed (${res.status})`;
    try {
      const data = await res.json();
      if (data?.detail) detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
    } catch {
      // keep default message
    }
    throw new Error(detail);
  }

  return res.json();
}

export async function deleteDocument(documentId) {
  const res = await fetch(`${DOCUMENTS_BASE}/${documentId}`, {
    method: "DELETE",
  });

  if (!res.ok) {
    let detail = `Delete failed (${res.status})`;
    try {
      const data = await res.json();
      if (data?.detail) detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
    } catch {
      // keep default message
    }
    throw new Error(detail);
  }

  return res.json();
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
