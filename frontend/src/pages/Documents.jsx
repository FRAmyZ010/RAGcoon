import React, { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
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
  Eye,
  X,
  UploadCloud,
  Loader2,
  RefreshCw,
  Check,
  CircleAlert,
} from "lucide-react";
import {
  deleteDocument,
  listDocuments,
  mapDocumentToRow,
  openDocumentPreview,
  uploadDocument,
  MAX_UPLOAD_BYTES,
  MAX_BATCH_UPLOAD_FILES,
} from "../services/documentsApi";
import { clearAuth } from "../services/authApi";

function splitCommaList(value) {
  if (!value || value === "—") return [];
  return String(value)
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean);
}

function statusChipClass(status) {
  if (status === "Ready") return "bg-green-100 text-green-800";
  if (status === "Failed") return "bg-red-100 text-red-800";
  return "bg-yellow-100 text-yellow-800";
}

export default function DocumentsManagement() {
  const navigate = useNavigate();
  const displayName = localStorage.getItem("username") || "Admin";
  const [activeMenuIndex, setActiveMenuIndex] = useState(null);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [filesData, setFilesData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [uploadQueue, setUploadQueue] = useState([]);
  const [uploadToast, setUploadToast] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [actionBusyId, setActionBusyId] = useState(null);
  const [menuPos, setMenuPos] = useState(null);
  const [detailsRow, setDetailsRow] = useState(null);
  const fileInputRef = useRef(null);
  const toastTimerRef = useRef(null);
  const uploadCancelRef = useRef(false);
  const uploadAbortRef = useRef(null);

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

  useEffect(() => {
    return () => {
      if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    };
  }, []);

  const showUploadToast = (summary) => {
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    setUploadToast(summary);
    toastTimerRef.current = setTimeout(() => setUploadToast(null), 5500);
  };

  const finishUploadSession = async ({ succeeded, failed, cancelled, total }) => {
    await fetchDocuments();
    setUploading(false);
    setIsUploadModalOpen(false);
    setUploadQueue([]);
    setUploadError("");
    uploadCancelRef.current = false;
    uploadAbortRef.current = null;
    if (succeeded > 0 || failed > 0 || cancelled > 0) {
      showUploadToast({ total, succeeded, failed, cancelled });
    }
  };

  const closeUploadModal = () => {
    if (uploading) {
      const ok = window.confirm(
        "ยกเลิกคิวอัปโหลดที่เหลือหรือไม่?\n\nไฟล์ที่อัปโหลดสำเร็จแล้วจะยังอยู่ในระบบ — เฉพาะไฟล์ที่รอคิว/กำลังทำจะถูกยกเลิก"
      );
      if (!ok) return;
      uploadCancelRef.current = true;
      uploadAbortRef.current?.abort();
      return;
    }

    const finished = uploadQueue.filter(
      (q) => q.status === "success" || q.status === "error" || q.status === "cancelled"
    );
    if (finished.length > 0) {
      const succeeded = finished.filter((q) => q.status === "success").length;
      const failed = finished.filter((q) => q.status === "error").length;
      const cancelled = finished.filter((q) => q.status === "cancelled").length;
      showUploadToast({
        total: finished.length,
        succeeded,
        failed,
        cancelled,
      });
    }
    setIsUploadModalOpen(false);
    setUploadQueue([]);
    setUploadError("");
  };

  const openUploadModal = () => {
    setUploadError("");
    setUploadQueue([]);
    uploadCancelRef.current = false;
    setIsUploadModalOpen(true);
  };

  const handleUploadFiles = async (fileList) => {
    const files = Array.from(fileList || []);
    if (files.length === 0) return;

    if (files.length > MAX_BATCH_UPLOAD_FILES) {
      setUploadError(`อัปโหลดได้สูงสุด ${MAX_BATCH_UPLOAD_FILES} ไฟล์ต่อครั้ง`);
      return;
    }

    for (const file of files) {
      if (!file.name.toLowerCase().endsWith(".pdf")) {
        setUploadError(`รองรับเฉพาะไฟล์ PDF เท่านั้น: ${file.name}`);
        return;
      }
      if (file.size > MAX_UPLOAD_BYTES) {
        setUploadError(`ไฟล์ใหญ่เกิน 25MB: ${file.name}`);
        return;
      }
    }

    const queue = files.map((file, index) => ({
      id: `${file.name}-${file.size}-${index}-${Date.now()}`,
      name: file.name,
      file,
      status: "pending",
      error: null,
    }));

    uploadCancelRef.current = false;
    const abortController = new AbortController();
    uploadAbortRef.current = abortController;

    setUploading(true);
    setUploadError("");
    setUploadQueue(queue);

    const statusById = Object.fromEntries(queue.map((q) => [q.id, "pending"]));
    let succeeded = 0;
    let failed = 0;

    const patchRow = (id, status, error = null) => {
      statusById[id] = status;
      setUploadQueue((prev) =>
        prev.map((row) => (row.id === id ? { ...row, status, error } : row))
      );
    };

    const cancelRemaining = (fromId = null) => {
      for (const item of queue) {
        const st = statusById[item.id];
        if (st === "pending" || st === "uploading" || item.id === fromId) {
          if (st === "success" || st === "error") continue;
          patchRow(item.id, "cancelled", "ยกเลิกโดยผู้ใช้");
        }
      }
    };

    for (const item of queue) {
      if (uploadCancelRef.current) {
        cancelRemaining();
        break;
      }

      patchRow(item.id, "uploading");

      try {
        await uploadDocument(item.file, { signal: abortController.signal });
        succeeded += 1;
        patchRow(item.id, "success");
      } catch (err) {
        const aborted =
          err?.name === "AbortError" ||
          String(err?.message || "").toLowerCase().includes("abort") ||
          uploadCancelRef.current;

        if (aborted) {
          cancelRemaining(item.id);
          break;
        }

        failed += 1;
        patchRow(item.id, "error", err.message || "Upload failed");
      }
    }

    if (uploadCancelRef.current) {
      cancelRemaining();
    }

    const cancelled = Object.values(statusById).filter((s) => s === "cancelled").length;
    const total = queue.length;
    const wasCancelled = uploadCancelRef.current;

    if (wasCancelled) {
      await new Promise((r) => setTimeout(r, 250));
      await finishUploadSession({
        succeeded,
        failed,
        cancelled,
        total,
      });
      return;
    }

    await fetchDocuments();
    setUploading(false);
    uploadAbortRef.current = null;

    if (failed === 0) {
      await new Promise((r) => setTimeout(r, 700));
      setIsUploadModalOpen(false);
      setUploadQueue([]);
      showUploadToast({ total, succeeded, failed, cancelled: 0 });
    }
  };

  const handleFileChange = (e) => {
    const files = e.target.files;
    if (files?.length) handleUploadFiles(files);
    e.target.value = "";
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragActive(false);
    const files = e.dataTransfer.files;
    if (files?.length) handleUploadFiles(files);
  };

  const closeActionMenu = () => {
    setActiveMenuIndex(null);
    setMenuPos(null);
  };

  const toggleActionMenu = (index, event) => {
    if (activeMenuIndex === index) {
      closeActionMenu();
      return;
    }
    const rect = event.currentTarget.getBoundingClientRect();
    setMenuPos({
      top: rect.bottom + 4,
      right: Math.max(8, window.innerWidth - rect.right),
    });
    setActiveMenuIndex(index);
  };

  const handleRemove = async (id) => {
    if (!window.confirm("ลบเอกสารนี้ถาวรหรือไม่?")) return;

    setActionBusyId(id);
    closeActionMenu();
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
    closeActionMenu();
    openDocumentPreview(id);
  };

  const handleDownload = (id, filename) => {
    closeActionMenu();
    const link = document.createElement("a");
    link.href = `/api/v1/documents/${id}/file?download=true`;
    link.download = filename || `document-${id}.pdf`;
    link.rel = "noopener";
    document.body.appendChild(link);
    link.click();
    link.remove();
  };

  return (
    <div className="relative flex h-screen w-screen overflow-hidden bg-gray-100 font-sans text-base text-gray-800 sm:text-lg">
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
            <div className="flex items-center gap-2 font-bold text-lg sm:text-xl">
              <span className="text-2xl">🦝</span>
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

        <button
          type="button"
          onClick={() => {
            clearAuth();
            navigate("/login", { replace: true });
          }}
          className="flex w-full items-center justify-between rounded-lg bg-white px-3 py-2 font-bold text-gray-900 hover:bg-gray-200"
        >
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
                {displayName.slice(0, 2).toUpperCase()}
              </div>
              <span className="font-bold text-gray-800 hidden sm:inline">{displayName}</span>
            </div>
          </div>
        </header>

        <div className="mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-gray-900">Documents Management</h1>
            <p className="text-sm text-gray-500 sm:text-base">
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
              onClick={openUploadModal}
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
            <table className="w-full text-left border-collapse min-w-[900px]">
              <thead className="bg-gray-50 border-b border-gray-200 text-gray-700 font-semibold text-sm">
                <tr>
                  <th className="py-3 px-4">Title</th>
                  <th className="py-3 px-3">Academic Year</th>
                  <th className="py-3 px-3">Source</th>
                  <th className="py-3 px-3">Status</th>
                  <th className="py-3 px-3">Date</th>
                  <th className="py-3 px-3 text-center">Details</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 text-sm sm:text-base">
                {loading && (
                  <tr>
                    <td colSpan={7} className="py-10 text-center text-gray-500">
                      <span className="inline-flex items-center gap-2">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Loading documents...
                      </span>
                    </td>
                  </tr>
                )}

                {!loading && filesData.length === 0 && (
                  <tr>
                    <td colSpan={7} className="py-10 text-center text-gray-500">
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
                          <span className="truncate max-w-[240px]" title={row.title}>
                            {row.title}
                          </span>
                        </div>
                      </td>
                      <td className="py-3 px-3 text-gray-600 whitespace-nowrap">{row.year}</td>
                      <td className="py-3 px-3 text-gray-600">
                        <span className="truncate max-w-[200px] block" title={row.source}>
                          {row.source}
                        </span>
                      </td>
                      <td className="py-3 px-3">
                        <span
                          className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
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
                      <td className="py-3 px-3 text-center">
                        <button
                          type="button"
                          onClick={() => setDetailsRow(row)}
                          className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-100"
                          aria-label={`View details for ${row.title}`}
                        >
                          <Eye className="h-4 w-4" />
                          <span className="hidden sm:inline">View</span>
                        </button>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          type="button"
                          onClick={(e) => toggleActionMenu(idx, e)}
                          disabled={actionBusyId === row.id}
                          className="p-1 rounded-lg hover:bg-gray-200 disabled:opacity-50"
                          aria-label="Open actions"
                        >
                          {actionBusyId === row.id ? (
                            <Loader2 className="h-4 w-4 animate-spin text-gray-500" />
                          ) : (
                            <MoreVertical className="h-4 w-4 text-gray-500" />
                          )}
                        </button>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </section>
      </main>

      {activeMenuIndex != null && menuPos && filesData[activeMenuIndex] && (
        <>
          <div className="fixed inset-0 z-40" onClick={closeActionMenu} aria-hidden />
          <div
            className="fixed z-50 w-44 rounded-xl border border-gray-200 bg-white p-1 text-left text-sm shadow-xl"
            style={{ top: menuPos.top, right: menuPos.right }}
          >
            <button
              type="button"
              onClick={() => handlePreview(filesData[activeMenuIndex].id)}
              className="flex w-full items-center gap-2 rounded-lg px-3 py-2 font-medium text-gray-700 hover:bg-gray-100"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              <span>Preview</span>
            </button>
            <button
              type="button"
              onClick={() =>
                handleDownload(
                  filesData[activeMenuIndex].id,
                  filesData[activeMenuIndex].filename
                )
              }
              className="flex w-full items-center gap-2 rounded-lg px-3 py-2 font-medium text-gray-700 hover:bg-gray-100"
            >
              <Download className="h-3.5 w-3.5" />
              <span>Download</span>
            </button>
            <button
              type="button"
              onClick={() => handleRemove(filesData[activeMenuIndex].id)}
              className="flex w-full items-center gap-2 rounded-lg px-3 py-2 font-medium text-red-600 hover:bg-red-50"
            >
              <Trash2 className="h-3.5 w-3.5" />
              <span>Remove</span>
            </button>
          </div>
        </>
      )}

      {detailsRow && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          onClick={() => setDetailsRow(null)}
        >
          <div
            className="flex max-h-[90vh] w-full max-w-xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl"
            role="dialog"
            aria-modal="true"
            aria-labelledby="document-details-title"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-3 border-b border-gray-100 bg-gray-50 px-6 py-4">
              <div className="min-w-0 space-y-2">
                <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                  Document Details
                </p>
                <h2
                  id="document-details-title"
                  className="text-lg font-bold leading-snug text-gray-900"
                >
                  {detailsRow.title}
                </h2>
                <div className="flex flex-wrap items-center gap-2">
                  <span
                    className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${statusChipClass(
                      detailsRow.status
                    )}`}
                  >
                    {detailsRow.status}
                  </span>
                  {detailsRow.year !== "—" && (
                    <span className="inline-flex rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700">
                      Year {detailsRow.year}
                    </span>
                  )}
                  {detailsRow.date !== "—" && (
                    <span className="inline-flex rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700">
                      {detailsRow.date}
                    </span>
                  )}
                </div>
              </div>
              <button
                type="button"
                onClick={() => setDetailsRow(null)}
                className="shrink-0 rounded-lg p-1 text-gray-400 hover:bg-white hover:text-gray-700"
                aria-label="Close details"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-4 overflow-y-auto px-6 py-5 text-sm">
              <section className="rounded-xl bg-gray-50 p-3">
                <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-gray-500">
                  Source
                </p>
                <div className="flex items-start gap-2 text-gray-900">
                  <FileText className="mt-0.5 h-4 w-4 shrink-0 text-[#800000]" />
                  <span className="break-all font-medium">{detailsRow.source}</span>
                </div>
              </section>

              <section>
                <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-gray-500">
                  Authors
                </p>
                {splitCommaList(detailsRow.authors).length > 0 ? (
                  <ul className="space-y-1.5">
                    {splitCommaList(detailsRow.authors).map((name) => (
                      <li
                        key={name}
                        className="rounded-lg bg-indigo-50 px-3 py-2 font-medium text-indigo-950"
                      >
                        {name}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-gray-400">—</p>
                )}
              </section>

              <section>
                <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-gray-500">
                  Advisor
                </p>
                <p className="rounded-lg bg-amber-50 px-3 py-2 font-medium text-amber-950">
                  {detailsRow.advisor}
                </p>
              </section>

              <section>
                <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-gray-500">
                  Supervisory Committee
                </p>
                {splitCommaList(detailsRow.supervisoryCommittee).length > 0 ? (
                  <ul className="space-y-1.5">
                    {splitCommaList(detailsRow.supervisoryCommittee).map((name) => (
                      <li
                        key={name}
                        className="rounded-lg bg-teal-50 px-3 py-2 font-medium text-teal-950"
                      >
                        {name}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-gray-400">—</p>
                )}
              </section>

              <section>
                <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-gray-500">
                  Keywords
                </p>
                {splitCommaList(detailsRow.keywords).length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {splitCommaList(detailsRow.keywords).map((kw) => (
                      <span
                        key={kw}
                        className="inline-flex rounded-full bg-rose-50 px-2.5 py-1 text-xs font-medium text-rose-800"
                      >
                        {kw}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-400">—</p>
                )}
              </section>
            </div>

            <div className="flex flex-wrap items-center justify-end gap-2 border-t border-gray-100 bg-gray-50 px-6 py-4">
              <button
                type="button"
                onClick={() => setDetailsRow(null)}
                className="rounded-lg px-4 py-2 text-sm font-semibold text-gray-600 hover:bg-gray-200"
              >
                Close
              </button>
              <button
                type="button"
                onClick={() => handleDownload(detailsRow.id, detailsRow.filename)}
                className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-semibold text-gray-800 hover:bg-gray-100"
              >
                <Download className="h-4 w-4" />
                Download
              </button>
              <button
                type="button"
                onClick={() => handlePreview(detailsRow.id)}
                className="inline-flex items-center gap-2 rounded-lg bg-[#800000] px-4 py-2 text-sm font-semibold text-white hover:bg-[#6a0000]"
              >
                <ExternalLink className="h-4 w-4" />
                Preview
              </button>
            </div>
          </div>
        </div>
      )}

      {isUploadModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl">
            <div className="mb-4 flex items-center justify-between border-b border-gray-100 pb-3">
              <h3 className="text-lg font-bold text-gray-900">Upload Senior Project PDFs</h3>
              <button
                onClick={closeUploadModal}
                className="text-gray-400 hover:text-black"
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
              } ${uploading ? "pointer-events-none opacity-70" : ""}`}
            >
              {uploading ? (
                <>
                  <Loader2 className="mb-2 h-10 w-10 animate-spin text-blue-500" />
                  <p className="text-base font-bold text-gray-700">กำลังอัปโหลดทีละไฟล์...</p>
                  <p className="mt-1 text-sm text-gray-400">ดูสถานะรายไฟล์ด้านล่าง</p>
                </>
              ) : (
                <>
                  <UploadCloud className="mb-2 h-10 w-10 text-blue-500" />
                  <p className="text-base font-bold text-gray-700">คลิกหรือลากไฟล์ PDF มาวาง</p>
                  <p className="mt-1 text-sm text-gray-400">
                    สูงสุด {MAX_BATCH_UPLOAD_FILES} ไฟล์ · PDF · Max 25MB / ไฟล์
                  </p>
                </>
              )}
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,application/pdf"
                multiple
                className="hidden"
                disabled={uploading}
                onChange={handleFileChange}
              />
            </label>

            {uploadError && (
              <div className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                {uploadError}
              </div>
            )}

            {uploadQueue.length > 0 && (
              <div className="mt-4 max-h-56 space-y-2 overflow-y-auto rounded-xl border border-gray-200 bg-gray-50 p-3">
                <div className="px-1 text-sm font-semibold text-gray-700">
                  คิวอัปโหลด · สำเร็จ{" "}
                  {uploadQueue.filter((q) => q.status === "success").length} / {uploadQueue.length}
                </div>
                {[
                  ...uploadQueue.filter(
                    (q) => q.status !== "success" && q.status !== "cancelled"
                  ),
                  ...uploadQueue.filter((q) => q.status === "cancelled"),
                  ...uploadQueue.filter((q) => q.status === "success"),
                ].map((item, index) => (
                  <div
                    key={item.id}
                    className={`upload-queue-item flex items-start gap-3 rounded-lg border px-3 py-2.5 text-sm transition-colors ${
                      item.status === "success"
                        ? "is-success border-green-200 bg-green-50 text-green-900"
                        : item.status === "error"
                          ? "border-red-200 bg-red-50 text-red-800"
                          : item.status === "cancelled"
                            ? "border-gray-300 bg-gray-100 text-gray-600"
                          : item.status === "uploading"
                            ? "is-uploading border-blue-200 bg-blue-50 text-blue-900"
                            : "border-gray-200 bg-white text-gray-700"
                    }`}
                    style={{ animationDelay: `${index * 40}ms` }}
                  >
                    <div className="mt-0.5 shrink-0">
                      {item.status === "success" && <Check className="h-4 w-4 text-green-600" />}
                      {item.status === "error" && <CircleAlert className="h-4 w-4 text-red-600" />}
                      {item.status === "cancelled" && <X className="h-4 w-4 text-gray-500" />}
                      {item.status === "uploading" && (
                        <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
                      )}
                      {item.status === "pending" && (
                        <span className="block h-4 w-4 rounded-full border-2 border-gray-300" />
                      )}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="truncate font-medium" title={item.name}>
                        {item.name}
                      </div>
                      <div className="mt-0.5 text-xs opacity-80 sm:text-sm">
                        {item.status === "pending" && "รอคิว"}
                        {item.status === "uploading" && "กำลังอัปโหลดและ ingest..."}
                        {item.status === "success" && "อัปโหลดเสร็จแล้ว"}
                        {item.status === "cancelled" && "ยกเลิกแล้ว"}
                        {item.status === "error" && (item.error || "ล้มเหลว")}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div className="mt-6 flex justify-end gap-2">
              <button
                onClick={closeUploadModal}
                className="rounded-lg border border-gray-300 px-4 py-2 font-semibold text-gray-600 hover:bg-gray-100"
              >
                {uploading
                  ? "Cancel"
                  : uploadQueue.some((q) => q.status === "error" || q.status === "cancelled")
                    ? "Close"
                    : "Cancel"}
              </button>
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                className="rounded-lg bg-blue-600 px-4 py-2 font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {uploading ? "Uploading..." : "Choose PDFs"}
              </button>
            </div>
          </div>
        </div>
      )}

      {uploadToast && (
        <div className="fixed bottom-6 right-6 z-[60] w-[min(100%-2rem,22rem)] animate-[upload-row-in_0.3s_ease-out] rounded-xl border border-gray-200 bg-white p-4 shadow-2xl">
          <div className="mb-2 flex items-start justify-between gap-2">
            <div className="font-bold text-gray-900">สรุปการอัปโหลด</div>
            <button
              type="button"
              onClick={() => setUploadToast(null)}
              className="text-gray-400 hover:text-gray-700"
              aria-label="Dismiss"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          <p className="text-sm text-gray-600 sm:text-base">
            สำเร็จ {uploadToast.succeeded} / {uploadToast.total}
            {uploadToast.failed > 0 ? ` · ล้มเหลว ${uploadToast.failed}` : ""}
            {uploadToast.cancelled > 0 ? ` · ยกเลิก ${uploadToast.cancelled}` : ""}
          </p>
          <ul className="mt-2 space-y-1 text-sm text-gray-700">
            <li className="flex items-center gap-2 text-green-700">
              <Check className="h-4 w-4" />
              {uploadToast.succeeded} ไฟล์พร้อมใช้งาน
            </li>
            {uploadToast.failed > 0 && (
              <li className="flex items-center gap-2 text-red-700">
                <CircleAlert className="h-4 w-4" />
                {uploadToast.failed} ไฟล์ไม่สำเร็จ
              </li>
            )}
            {uploadToast.cancelled > 0 && (
              <li className="flex items-center gap-2 text-gray-600">
                <X className="h-4 w-4" />
                {uploadToast.cancelled} ไฟล์ถูกยกเลิก
              </li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
