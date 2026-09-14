import React, { useState } from "react";
import { Link } from "react-router-dom";
import {
  FileText,
  MoreVertical,
  Plus,
  ChevronDown,
  LayoutDashboard,
  FolderClosed,
  MessageSquare,
  LogOut,
  Bell,
  PanelLeftClose,
  Download,
  Copy,
  Edit2,
  Trash2,
  X,
  UploadCloud,
} from "lucide-react";

export default function DocumentsManagement() {
  const [activeMenuIndex, setActiveMenuIndex] = useState(null);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [isRenameModalOpen, setIsRenameModalOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [newFileName, setNewFileName] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const [filesData, setFilesData] = useState([
    { id: 1, title: "ProjectPetFeeder", year: "2022", category: "IOT", status: "Processing", date: "12 Jan 2025" },
    { id: 2, title: "ProjectWebapplication", year: "2023", category: "Web Application", status: "Ready", date: "12 Jan 2025" },
    { id: 3, title: "Networkmonitoring", year: "2023", category: "Network", status: "Processing", date: "12 Jan 2025" },
    { id: 4, title: "Preprojectnetwork", year: "2022", category: "Network", status: "Failed", date: "12 Jan 2025" },
    { id: 5, title: "ProjectFulldocument", year: "2021", category: "IOT", status: "Processing", date: "12 Jan 2025" },
  ]);

  const toggleActionMenu = (index) => {
    setActiveMenuIndex(activeMenuIndex === index ? null : index);
  };

  const handleRemove = (id) => {
    setFilesData(filesData.filter((file) => file.id !== id));
    setActiveMenuIndex(null);
  };

  const handleOpenRename = (file) => {
    setSelectedFile(file);
    setNewFileName(file.title);
    setIsRenameModalOpen(true);
    setActiveMenuIndex(null);
  };

  const handleSaveRename = (e) => {
    e.preventDefault();
    setFilesData(
      filesData.map((f) => (f.id === selectedFile.id ? { ...f, title: newFileName } : f))
    );
    setIsRenameModalOpen(false);
  };

  return (
    <div className="flex h-screen w-screen bg-gray-100 font-sans text-xs sm:text-sm text-gray-800 overflow-hidden relative">
      {/* MOBILE BACKDROP */}
      {sidebarOpen && (
        <div
          onClick={() => setSidebarOpen(false)}
          className="fixed inset-0 bg-black/50 z-30 lg:hidden"
        />
      )}

      {/* ---------------- SIDEBAR ---------------- */}
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
            <button onClick={() => setSidebarOpen(false)} className="lg:hidden text-gray-400 hover:text-white">
              ✕
            </button>
          </div>

          <nav className="space-y-1.5">
            <Link to="/dashboard" className="flex items-center gap-3 rounded-lg px-3 py-2 text-gray-300 hover:bg-white/10">
              <LayoutDashboard className="h-4 w-4" />
              <span>Dashboard</span>
            </Link>
            <Link to="/documents" className="flex items-center gap-3 rounded-lg bg-white px-3 py-2 font-bold text-gray-900">
              <FolderClosed className="h-4 w-4" />
              <span>Documents</span>
            </Link>
            <Link to="/chat" className="flex items-center gap-3 rounded-lg px-3 py-2 text-gray-300 hover:bg-white/10">
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

      {/* ---------------- MAIN CONTENT ---------------- */}
      <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 min-w-0">
        {/* Top Header */}
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

        {/* Action Header */}
        <div className="mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-lg sm:text-xl font-bold text-gray-900">Documents Management</h1>
            <p className="text-xs text-gray-500">จัดการและอัปโหลดไฟล์โครงงาน Senior Project เข้าสู่คลังข้อมูล RAG Engine</p>
          </div>

          <button
            onClick={() => setIsUploadModalOpen(true)}
            className="flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2 font-bold text-white hover:bg-blue-700 shadow-sm shrink-0"
          >
            <Plus className="h-4 w-4" />
            <span>Upload File</span>
          </button>
        </div>

        {/* All Files Table */}
        <section className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse min-w-[600px]">
              <thead className="bg-gray-50 border-b border-gray-200 text-gray-700 font-semibold text-xs">
                <tr>
                  <th className="py-3 px-4">Title</th>
                  <th className="py-3 px-3">Year</th>
                  <th className="py-3 px-3">Category</th>
                  <th className="py-3 px-3">Status</th>
                  <th className="py-3 px-3">Date</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 text-xs sm:text-sm">
                {filesData.map((row, idx) => (
                  <tr key={row.id} className="hover:bg-gray-50 transition">
                    <td className="py-3 px-4 font-bold text-gray-900 flex items-center gap-2">
                      <FileText className="h-4 w-4 text-[#800000] shrink-0" />
                      <span className="truncate max-w-[180px] sm:max-w-none">{row.title}</span>
                    </td>
                    <td className="py-3 px-3 text-gray-600">{row.year}</td>
                    <td className="py-3 px-3 text-gray-600">{row.category}</td>
                    <td className="py-3 px-3">
                      <span className={`px-2 py-0.5 rounded-full text-[11px] font-semibold ${
                        row.status === "Ready" ? "bg-green-100 text-green-700" :
                        row.status === "Failed" ? "bg-red-100 text-red-700" : "bg-yellow-100 text-yellow-700"
                      }`}>
                        {row.status}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-gray-500">{row.date}</td>
                    <td className="py-3 px-4 text-right relative">
                      <button onClick={() => toggleActionMenu(idx)} className="p-1 rounded-lg hover:bg-gray-200">
                        <MoreVertical className="h-4 w-4 text-gray-500" />
                      </button>

                      {activeMenuIndex === idx && (
                        <div className="absolute right-4 top-10 z-20 w-36 rounded-xl bg-white p-1 shadow-xl border border-gray-200 text-left text-xs">
                          <button onClick={() => handleOpenRename(row)} className="flex w-full items-center gap-2 rounded-lg px-3 py-2 font-medium text-gray-700 hover:bg-gray-100">
                            <Edit2 className="h-3.5 w-3.5" />
                            <span>Rename</span>
                          </button>
                          <button onClick={() => handleRemove(row.id)} className="flex w-full items-center gap-2 rounded-lg px-3 py-2 font-medium text-red-600 hover:bg-red-50">
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

      {/* MODAL UPLOAD FILE */}
      {isUploadModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
            <div className="mb-4 flex items-center justify-between border-b border-gray-100 pb-3">
              <h3 className="text-base font-bold text-gray-900">Upload New Senior Project File</h3>
              <button onClick={() => setIsUploadModalOpen(false)} className="text-gray-400 hover:text-black">
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-300 p-8 hover:bg-gray-50 cursor-pointer text-center">
              <UploadCloud className="h-10 w-10 text-blue-500 mb-2" />
              <p className="font-bold text-gray-700 text-sm">Drag and drop PDF files here</p>
              <p className="text-xs text-gray-400 mt-1">Supported format: PDF (Max 25MB)</p>
            </div>
            <div className="mt-6 flex justify-end gap-2">
              <button onClick={() => setIsUploadModalOpen(false)} className="rounded-lg border border-gray-300 px-4 py-2 font-semibold text-gray-600 hover:bg-gray-100">
                Cancel
              </button>
              <button onClick={() => setIsUploadModalOpen(false)} className="rounded-lg bg-blue-600 px-4 py-2 font-semibold text-white hover:bg-blue-700">
                Upload
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}