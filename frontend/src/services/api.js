// src/services/api.js
const API_BASE_URL = "http://localhost:8000/api/v1"; // อัปเดต Base URL เป็น /api/v1 ตาม Spec

// ดึง Token จาก LocalStorage
const getAuthHeaders = () => {
  const token = localStorage.getItem("token");
  return {
    Authorization: `Bearer ${token}`,
  };
};

// 🔵 1. ดึงรายการเอกสารทั้งหมด (GET /api/v1/documents)
export async function fetchDocumentsApi() {
  const response = await fetch(`${API_BASE_URL}/documents`, {
    method: "GET",
    headers: {
      ...getAuthHeaders(),
    },
  });

  if (!response.ok) throw new Error("Failed to fetch documents");
  return response.json();
}

// 🔵 2. อัปโหลดไฟล์เอกสาร (POST /api/v1/documents/upload)
export async function uploadDocumentApi(file, projectDetails) {
  const formData = new FormData();
  
  // แนบไฟล์และข้อมูล Meta ตาม Form-Data ใน API Spec
  formData.append("file", file);
  formData.append("project_title", projectDetails.project_title || "");
  formData.append("academic_year", projectDetails.academic_year || 2024);
  formData.append("authors", projectDetails.authors || "");
  formData.append("advisor", projectDetails.advisor || "");

  const response = await fetch(`${API_BASE_URL}/documents/upload`, {
    method: "POST",
    headers: {
      ...getAuthHeaders(), // ต้องใช้ Bearer JWT[cite: 1]
    },
    body: formData,
  });

  if (!response.ok) throw new Error("Upload failed");
  return response.json();
}

// 🔵 3. ลบเอกสาร (DELETE /api/v1/documents/{id})
export async function deleteDocumentApi(documentId) {
  const response = await fetch(`${API_BASE_URL}/documents/${documentId}`, {
    method: "DELETE",
    headers: {
      ...getAuthHeaders(), // ต้องใช้ Bearer JWT[cite: 1]
    },
  });

  if (!response.ok) throw new Error("Delete failed");
  return response.json();
}