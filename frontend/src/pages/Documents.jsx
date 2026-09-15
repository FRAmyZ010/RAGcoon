import React, { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  FileText,
  MoreVertical,
  Plus,
  LayoutDashboard,
  FolderClosed,
  MessageSquare,
  LogOut,
  Bell,
  Trash2,
  Download,
  ExternalLink,
  X,
  UploadCloud,
  Loader2,
  RefreshCw,
} from "lucide-react";
import {
  deleteDocument,
  listDocuments,
  mapDocumentToRow,
  openDocumentPreview,
  uploadDocument,
  MAX_UPLOAD_BYTES,
} from "../services/documentsApi";

export default function DocumentsManagement() {
  const [activeMenuIndex, setActiveMenuIndex] = useState(null);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [filesData, setFilesData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [dragActive, setDragActive] = useState(false);
  const [actionBusyId, setActionBusyId] = useState(null);
  const fileInputRef = useRef(null);

  const fetchDocuments = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const docs = await listDocuments();
      setFilesData(docs.map(mapDocumentToRow));
    } catch (err) {
      setError(err.message || "Failed to load documents");
      setFilesData([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  const toggleActionMenu = (index) => {
    setActiveMenuIndex(activeMenuIndex === index ? null : index);
  };

  const handleRemove = async (id) => {
    if (!window.confirm("ลบเอกสารนี้ถาวรหรือไม่?")) return;

    setActionBusyId(id);
    setActiveMenuIndex(null);
    try {
      await deleteDocument(id);
      setFilesData((prev) => prev.filter((file) => file.id !== id));
    } catch (err) {
      setError(err.message || "Delete failed");
    } finally {
      setActionBusyId(null);
    }
  };

  const handlePreview = (id) => {
    setActiveMenuIndex(null);
    openDocumentPreview(id);
  };

  const handleDownload = (id, filename) => {
    setActiveMenuIndex(null);
    const link = document.createElement("a");
    link.href = `/api/v1/documents/${id}/file?download=true`;
    link.download = filename || `document-${id}.pdf`;
    link.rel = "noopener";
    document.body.appendChild(link);
    link.click();
    link.remove();
  };

  const handleUploadFile = async (file) => {
    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setUploadError("รองรับเฉพาะไฟล์ PDF เท่านั้น");
      return;
    }

    if (file.size > MAX_UPLOAD_BYTES) {
      setUploadError("ไฟล์ใหญ่เกิน 25MB");
      return;
    }

    setUploading(true);
    setUploadError("");
    try {
      await uploadDocument(file);
      setIsUploadModalOpen(false);
      await fetchDocuments();
    } catch (err) {
      setUploadError(err.message || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) handleUploadFile(file);
    e.target.value = "";
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragActive(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleUploadFile(file);
  };

  return (
    <div className="flex h-screen w-screen bg-gray-100 font-sans text-xs sm:text-sm text-gray-800 overflow-hidden relative">
      {sidebarOpen && (
        <div
          onClick={() => setSidebarOpen(false)}
          className="fixed inset-0 bg-black/50 z-30 lg:hidden"
        />
      )}

      <aside
        className={`fixed lg:static inset-y-0 left-0 z-40 flex w-64 shrink-0 flex-col justify-between bg-[#2d2d2d] p-4 text-white transition-transform duration-300 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        }`}
      >
        <div>
          <div className="mb-6 flex items-center justify-between">
            <div className="flex items-center gap-2 font-bold text-base sm:text-lg">
              <span className="text-xl">🦝</span>
              <span>RAGcoon</span>
            </div>
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden text-gray-400 hover:text-white"
            >
              ✕
            </button>
          </div>

          <nav className="space-y-1.5">
            <Link
              to="/dashboard"
              className="flex items-center gap-3 rounded-lg px-3 py-2 text-gray-300 hover:bg-white/10"
            >
              <LayoutDashboard className="h-4 w-4" />
              <span>Dashboard</span>
            </Link>
            <Link
              to="/documents"
              className="flex items-center gap-3 rounded-lg bg-white px-3 py-2 font-bold text-gray-900"
            >
              <FolderClosed className="h-4 w-4" />
              <span>Documents</span>
            </Link>
            <Link
              to="/chat"
              className="flex items-center gap-3 rounded-lg px-3 py-2 text-gray-300 hover:bg-white/10"
            >
              <MessageSquare className="h-4 w-4" />
              <span>Chat Workspace</span>
            </Link>
          </nav>
        </div>

        <button className="flex w-full items-center justify-between rounded-lg bg-white px-3 py-2 font-bold text-gray-900 hover:bg-gray-200">
          <span>Log Out</span>
          <LogOut className="h-4 w-4" />
        </button>
      </aside>

      <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 min-w-0">
        <header className="mb-6 flex items-center justify-between">
          <button
            onClick={() => setSidebarOpen(true)}
            className="lg:hidden rounded-lg p-2 bg-white shadow-sm hover:bg-gray-50"
          >
            ☰
          </button>
          <div className="flex items-center gap-3 ml-auto">
            <Bell className="h-5 w-5 cursor-pointer text-gray-600 hover:text-black" />
            <div className="flex items-center gap-2">
              <div className="h-7 w-7 rounded-full bg-[#800000] text-white font-bold text-xs flex items-center justify-center">
                MJ
              </div>
              <span className="font-bold text-gray-800 hidden sm:inline">Marry Jann</span>
            </div>
          </div>
        </header>

        <div className="mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-lg sm:text-xl font-bold text-gray-900">Documents Management</h1>
            <p className="text-xs text-gray-500">
              จัดการและอัปโหลดไฟล์โครงงาน Senior Project เข้าสู่คลังข้อมูล RAG Engine
            </p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={fetchDocuments}
              disabled={loading}
              className="flex items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 font-semibold text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              title="Refresh"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              <span className="hidden sm:inline">Refresh</span>
            </button>
            <button
              onClick={() => {
                setUploadError("");
                setIsUploadModalOpen(true);
              }}
              className="flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2 font-bold text-white hover:bg-blue-700 shadow-sm"
            >
              <Plus className="h-4 w-4" />
              <span>Upload File</span>
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <section className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse min-w-[1200px]">
              <thead className="bg-gray-50 border-b border-gray-200 text-gray-700 font-semibold text-xs">
                <tr>
                  <th className="py-3 px-4">Title</th>
                  <th className="py-3 px-3">Authors</th>
                  <th className="py-3 px-3">Advisor</th>
                  <th className="py-3 px-3">Academic Year</th>
                  <th className="py-3 px-3">Keywords</th>
                  <th className="py-3 px-3">Supervisory Committee</th>
                  <th className="py-3 px-3">Status</th>
                  <th className="py-3 px-3">Date</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 text-xs sm:text-sm">
                {loading && (
                  <tr>
                    <td colSpan={9} className="py-10 text-center text-gray-500">
                      <span className="inline-flex items-center gap-2">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Loading documents...
                      </span>
                    </td>
                  </tr>
                )}

                {!loading && filesData.length === 0 && (
                  <tr>
                    <td colSpan={9} className="py-10 text-center text-gray-500">
                      ยังไม่มีเอกสาร — กด Upload File เพื่อเพิ่ม PDF
                    </td>
                  </tr>
                )}

                {!loading &&
                  filesData.map((row, idx) => (
                    <tr key={row.id} className="hover:bg-gray-50 transition">
                      <td className="py-3 px-4 font-bold text-gray-900">
                        <div className="flex items-center gap-2">
                          <FileText className="h-4 w-4 text-[#800000] shrink-0" />
                          <span className="truncate max-w-[200px]" title={row.title}>
                            {row.title}
                          </span>
                        </div>
                      </td>
                      <td className="py-3 px-3 text-gray-600">
                        <span className="line-clamp-2 max-w-[160px]" title={row.authors}>
                          {row.authors}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-gray-600">
                        <span className="line-clamp-2 max-w-[160px]" title={row.advisor}>
                          {row.advisor}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-gray-600 whitespace-nowrap">{row.year}</td>
                      <td className="py-3 px-3 text-gray-600">
                        <span className="line-clamp-2 max-w-[180px]" title={row.keywords}>
                          {row.keywords}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-gray-600">
                        <span className="line-clamp-2 max-w-[180px]" title={row.supervisoryCommittee}>
                          {row.supervisoryCommittee}
                        </span>
                      </td>
                      <td className="py-3 px-3">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[11px] font-semibold ${
                            row.status === "Ready"
                              ? "bg-green-100 text-green-700"
                              : row.status === "Failed"
                                ? "bg-red-100 text-red-700"
                                : "bg-yellow-100 text-yellow-700"
                          }`}
                        >
                          {row.status}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-gray-500 whitespace-nowrap">{row.date}</td>
                      <td className="py-3 px-4 text-right relative">
                        <button
                          onClick={() => toggleActionMenu(idx)}
                          disabled={actionBusyId === row.id}
                          className="p-1 rounded-lg hover:bg-gray-200 disabled:opacity-50"
                        >
                          {actionBusyId === row.id ? (
                            <Loader2 className="h-4 w-4 animate-spin text-gray-500" />
                          ) : (
                            <MoreVertical className="h-4 w-4 text-gray-500" />
                          )}
                        </button>

                        {activeMenuIndex === idx && (
                          <div className="absolute right-4 top-10 z-20 w-40 rounded-xl bg-white p-1 shadow-xl border border-gray-200 text-left text-xs">
                            <button
                              onClick={() => handlePreview(row.id)}
                              className="flex w-full items-center gap-2 rounded-lg px-3 py-2 font-medium text-gray-700 hover:bg-gray-100"
                            >
                              <ExternalLink className="h-3.5 w-3.5" />
                              <span>Preview</span>
                            </button>
                            <button
                              onClick={() => handleDownload(row.id, row.filename)}
                              className="flex w-full items-center gap-2 rounded-lg px-3 py-2 font-medium text-gray-700 hover:bg-gray-100"
                            >
                              <Download className="h-3.5 w-3.5" />
                              <span>Download</span>
                            </button>
                            <button
                              onClick={() => handleRemove(row.id)}
                              className="flex w-full items-center gap-2 rounded-lg px-3 py-2 font-medium text-red-600 hover:bg-red-50"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                              <span>Remove</span>
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </section>
      </main>

      {isUploadModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
            <div className="mb-4 flex items-center justify-between border-b border-gray-100 pb-3">
              <h3 className="text-base font-bold text-gray-900">Upload New Senior Project File</h3>
              <button
                onClick={() => !uploading && setIsUploadModalOpen(false)}
                disabled={uploading}
                className="text-gray-400 hover:text-black disabled:opacity-50"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <label
              onDragOver={(e) => {
                e.preventDefault();
                setDragActive(true);
              }}
              onDragLeave={() => setDragActive(false)}
              onDrop={handleDrop}
              className={`flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 cursor-pointer text-center transition ${
                dragActive
                  ? "border-blue-500 bg-blue-50"
                  : "border-gray-300 hover:bg-gray-50"
              }`}
            >
              {uploading ? (
                <>
                  <Loader2 className="h-10 w-10 text-blue-500 mb-2 animate-spin" />
                  <p className="font-bold text-gray-700 text-sm">Uploading & ingesting...</p>
                  <p className="text-xs text-gray-400 mt-1">อาจใช้เวลาสักครู่เพราะระบบทำ embedding</p>
                </>
              ) : (
                <>
                  <UploadCloud className="h-10 w-10 text-blue-500 mb-2" />
                  <p className="font-bold text-gray-700 text-sm">คลิกหรือลากไฟล์ PDF มาวาง</p>
                  <p className="text-xs text-gray-400 mt-1">Supported format: PDF (Max 25MB)</p>
                </>
              )}
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,application/pdf"
                className="hidden"
                disabled={uploading}
                onChange={handleFileChange}
              />
            </label>

            {uploadError && (
              <div className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
                {uploadError}
              </div>
            )}

            <div className="mt-6 flex justify-end gap-2">
              <button
                onClick={() => setIsUploadModalOpen(false)}
                disabled={uploading}
                className="rounded-lg border border-gray-300 px-4 py-2 font-semibold text-gray-600 hover:bg-gray-100 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                className="rounded-lg bg-blue-600 px-4 py-2 font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {uploading ? "Uploading..." : "Choose PDF"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
