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
  Paperclip,
  Download,
  Copy,
  Edit2,
  Trash2,
  X,
  UploadCloud,
} from "lucide-react";

export default function DocumentsManagement() {
  // State ควบคุม Dropdown Menu และ Modals
  const [activeMenuIndex, setActiveMenuIndex] = useState(null);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [isRenameModalOpen, setIsRenameModalOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [newFileName, setNewFileName] = useState("");

  // ข้อมูลรายการไฟล์ (ใช้ State เพื่อรองรับ Dynamic Actions)
  const [filesData, setFilesData] = useState([
    { id: 1, title: "ProjectPetFeeder", year: "2022", category: "IOT", status: "Processing", date: "12 Jan 2025" },
    { id: 2, title: "ProjectWebapplication", year: "2023", category: "Web Application", status: "Ready", date: "12 Jan 2025" },
    { id: 3, title: "Networkmonitoring", year: "2023", category: "Network", status: "Processing", date: "12 Jan 2025" },
    { id: 4, title: "Preprojectnetwork", year: "2022", category: "Network", status: "Failed", date: "12 Jan 2025" },
    { id: 5, title: "ProjectFulldocument", year: "2021", category: "IOT", status: "Processing", date: "12 Jan 2025" },
    { id: 6, title: "Embeddedsystemproject", year: "2020", category: "IOT", status: "Processing", date: "12 Jan 2025" },
    { id: 7, title: "ProjectMachine", year: "2022", category: "Machine Learning", status: "Ready", date: "11 Jan 2025" },
    { id: 8, title: "Pre-project_MFU-WIFI", year: "2021", category: "Network", status: "Processing", date: "11 Jan 2025" },
    { id: 9, title: "ProjectPetFeeder", year: "2022", category: "IOT", status: "Processing", date: "10 Jan 2025" },
  ]);

  const recentFiles = [
    { id: 1, name: "PROJECT-PetFeeder-Finalize", size: "228 KB pdf" },
    { id: 2, name: "PROJECT-PetFeeder-Finalize", size: "228 KB pdf" },
    { id: 3, name: "PROJECT-PetFeeder-Finalize", size: "228 KB pdf" },
  ];

  // ================= Action Handlers =================
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
    <div className="flex h-screen w-full bg-[#C8C8C8] font-mono text-xs text-[#353535]">
      {/* ---------------- SIDEBAR ---------------- */}
      <aside className="flex w-60 flex-col justify-between bg-[#353535] p-4 text-white flex-shrink-0">
        <div>
          <div className="mb-6 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gray-200 text-black">
                🦝
              </div>
              <span className="text-sm font-bold tracking-wide">RAGcoon</span>
            </div>
            <PanelLeftClose className="h-4 w-4 cursor-pointer text-gray-400 hover:text-white" />
          </div>

          <nav className="space-y-1.5">
            <Link to="/dashboard" className="flex items-center gap-3 rounded-lg px-3 py-2 text-gray-300 hover:bg-gray-700">
              <LayoutDashboard className="h-4 w-4" />
              <span>Dashboard</span>
            </Link>
            <Link to="/documents" className="flex items-center gap-3 rounded-lg bg-white px-3 py-2 font-bold text-[#353535]">
              <FolderClosed className="h-4 w-4" />
              <span>Documents Management</span>
            </Link>
            <Link to="/chat" className="flex items-center gap-3 rounded-lg px-3 py-2 text-gray-300 hover:bg-gray-700">
              <MessageSquare className="h-4 w-4" />
              <span>Feedback</span>
            </Link>
          </nav>
        </div>

        <button className="flex w-full items-center justify-between rounded-md bg-white px-3 py-1.5 font-bold text-[#353535] hover:bg-gray-100">
          <span>Log Out</span>
          <LogOut className="h-3.5 w-3.5" />
        </button>
      </aside>

      {/* ---------------- MAIN CONTENT ---------------- */}
      <main className="flex-1 overflow-y-auto p-8">
        {/* Top Header */}
        <header className="mb-6 flex items-center justify-end gap-3">
          <Bell className="h-4 w-4 cursor-pointer text-gray-700 hover:text-black" />
          <div className="flex items-center gap-2">
            <div className="h-5 w-5 rounded-full bg-[#800000]" />
            <span className="font-bold text-[#353535]">Marry Jann</span>
          </div>
        </header>

        {/* Recently Modified Section */}
        <section className="mb-8">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-xs font-bold text-[#353535]">Recently modified</h2>
            
            <div className="flex items-center gap-2">
              <Link
                to="/chat"
                title="เปิดหน้าต่าง Chat"
                className="flex items-center justify-center rounded bg-white p-1.5 text-gray-700 hover:bg-gray-100 shadow-sm"
              >
                <Paperclip className="h-4 w-4" />
              </Link>
              <button
                onClick={() => setIsUploadModalOpen(true)}
                className="flex items-center gap-1.5 rounded bg-[#1D61E7] px-3 py-1.5 font-bold text-white hover:bg-blue-700 shadow-sm"
              >
                <Plus className="h-3.5 w-3.5" />
                <span>Upload file</span>
              </button>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            {recentFiles.map((file) => (
              <div key={file.id} className="flex items-center justify-between rounded bg-white p-3 shadow-sm">
                <div className="flex items-center gap-3">
                  <FileText className="h-5 w-5 text-gray-700" />
                  <div>
                    <div className="font-bold text-[#353535]">{file.name}</div>
                    <div className="text-[10px] text-gray-400">{file.size}</div>
                  </div>
                </div>
                <MoreVertical className="h-4 w-4 cursor-pointer text-gray-400 hover:text-gray-600" />
              </div>
            ))}
          </div>
        </section>

        {/* All Files Section */}
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-xs font-bold text-[#353535]">All files</h2>
            <div className="flex gap-2">
              {["Category", "Modified", "Years"].map((filter) => (
                <button key={filter} className="flex items-center gap-1 rounded bg-[#E5E5E5] px-2.5 py-1 text-gray-700 hover:bg-gray-300">
                  <span>{filter}</span>
                  <ChevronDown className="h-3 w-3" />
                </button>
              ))}
            </div>
          </div>

          {/* Table */}
          <div className="overflow-visible rounded bg-white shadow-sm">
            <table className="w-full text-left border-collapse">
              <thead className="bg-[#E5E5E5] text-gray-900 font-bold">
                <tr>
                  <th className="py-2.5 pl-4">Title</th>
                  <th className="py-2.5">Year</th>
                  <th className="py-2.5">Category</th>
                  <th className="py-2.5">Status</th>
                  <th className="py-2.5">Date</th>
                  <th className="py-2.5 pr-4"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 text-[#353535]">
                {filesData.map((row, idx) => (
                  <tr key={row.id} className="hover:bg-gray-50 relative">
                    <td className="flex items-center gap-2 py-2.5 pl-4 font-bold">
                      <FileText className="h-4 w-4 text-[#800000]" />
                      <span>{row.title}</span>
                    </td>
                    <td className="py-2.5">{row.year}</td>
                    <td className="py-2.5">{row.category}</td>
                    <td className="py-2.5">{row.status}</td>
                    <td className="py-2.5">{row.date}</td>
                    <td className="py-2.5 pr-4 text-right relative">
                      <button onClick={() => toggleActionMenu(idx)} className="p-1 rounded hover:bg-gray-200">
                        <MoreVertical className="h-4 w-4 text-gray-500" />
                      </button>

                      {/* Dropdown Action Menu */}
                      {activeMenuIndex === idx && (
                        <div className="absolute right-4 top-8 z-20 w-44 rounded bg-[#E5E7EB] p-1 shadow-lg text-left border border-gray-300">
                          <button className="flex w-full items-center gap-2 rounded px-3 py-1.5 font-bold text-gray-800 hover:bg-gray-300">
                            <Download className="h-3.5 w-3.5" />
                            <span>Download</span>
                          </button>
                          <button className="flex w-full items-center gap-2 rounded px-3 py-1.5 font-bold text-gray-800 hover:bg-gray-300">
                            <Copy className="h-3.5 w-3.5" />
                            <span>Copy</span>
                          </button>
                          <button onClick={() => handleOpenRename(row)} className="flex w-full items-center gap-2 rounded px-3 py-1.5 font-bold text-gray-800 hover:bg-gray-300">
                            <Edit2 className="h-3.5 w-3.5" />
                            <span>Rename</span>
                          </button>
                          <button onClick={() => handleRemove(row.id)} className="flex w-full items-center gap-2 rounded px-3 py-1.5 font-bold text-red-600 hover:bg-gray-300">
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

      {/* ---------------- MODAL 1: UPLOAD FILE ---------------- */}
      {isUploadModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
            <div className="mb-4 flex items-center justify-between border-b pb-3">
              <h3 className="text-sm font-bold text-gray-800">Upload New File</h3>
              <button onClick={() => setIsUploadModalOpen(false)}>
                <X className="h-4 w-4 text-gray-500 hover:text-black" />
              </button>
            </div>
            
            <div className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-gray-300 p-8 hover:bg-gray-50 cursor-pointer">
              <UploadCloud className="h-10 w-10 text-gray-400 mb-2" />
              <p className="font-bold text-gray-600">Drag and drop files here</p>
              <p className="text-[10px] text-gray-400">Supported formats: PDF, DOCX, TXT</p>
            </div>

            <div className="mt-6 flex justify-end gap-2">
              <button
                onClick={() => setIsUploadModalOpen(false)}
                className="rounded border border-gray-300 px-4 py-1.5 font-bold text-gray-600 hover:bg-gray-100"
              >
                Cancel
              </button>
              <button
                onClick={() => setIsUploadModalOpen(false)}
                className="rounded bg-[#1D61E7] px-4 py-1.5 font-bold text-white hover:bg-blue-700"
              >
                Upload
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ---------------- MODAL 2: RENAME FILE ---------------- */}
      {isRenameModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-sm rounded-lg bg-white p-6 shadow-xl">
            <div className="mb-4 flex items-center justify-between border-b pb-3">
              <h3 className="text-sm font-bold text-gray-800">Rename File</h3>
              <button onClick={() => setIsRenameModalOpen(false)}>
                <X className="h-4 w-4 text-gray-500 hover:text-black" />
              </button>
            </div>

            <form onSubmit={handleSaveRename}>
              <div className="mb-4">
                <label className="mb-1 block text-[11px] font-bold text-gray-600">File Title</label>
                <input
                  type="text"
                  value={newFileName}
                  onChange={(e) => setNewFileName(e.target.value)}
                  className="w-full rounded border border-gray-300 p-2 text-xs outline-none focus:border-blue-500"
                />
              </div>

              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setIsRenameModalOpen(false)}
                  className="rounded border border-gray-300 px-4 py-1.5 font-bold text-gray-600 hover:bg-gray-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded bg-[#1D61E7] px-4 py-1.5 font-bold text-white hover:bg-blue-700"
                >
                  Save
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}