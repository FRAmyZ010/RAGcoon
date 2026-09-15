import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { 
  FileText, 
  Upload, 
  MessageSquare, 
  ChevronDown, 
  MoreVertical, 
  Trash2 
} from "lucide-react";
import UploadModal from "../components/ui/UploadModal";
import { fetchDocumentsApi, deleteDocumentApi } from "../services/api";

export default function Documents() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [activeMenuId, setActiveMenuId] = useState(null);

  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    try {
      setLoading(true);
      const data = await fetchDocumentsApi();
      setDocuments(data);
    } catch (error) {
      console.error("API Error:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (documentId) => {
    if (window.confirm("คุณต้องการลบเอกสารนี้ออกจากระบบใช่หรือไม่?")) {
      try {
        await deleteDocumentApi(documentId);
        setDocuments(documents.filter((doc) => doc.document_id !== documentId));
        setActiveMenuId(null);
      } catch (error) {
        alert("ลบไฟล์ไม่สำเร็จ");
      }
    }
  };

  return (
    // Responsive Container: ปรับ Padding ตามขนาดหน้าจอ
    <div className="p-4 sm:p-6 lg:p-8 font-mono text-[#353535] max-w-[1400px] mx-auto w-full">
      
      {/* 🔴 Section 1: Recently modified (Responsive Grid: 1 Col -> 2 Col -> 3 Col) */}
      <div className="mb-6 sm:mb-8">
        <h2 className="text-sm sm:text-base font-bold mb-3 sm:mb-4">Recently modified</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
          {documents.slice(0, 3).map((doc) => (
            <div 
              key={doc.document_id || doc.id} 
              className="bg-white p-3.5 sm:p-4 rounded-xl border border-gray-200 shadow-sm flex items-start justify-between"
            >
              <div className="flex items-start gap-3 min-w-0">
                <div className="p-2 bg-red-50 rounded-lg text-[#800000] shrink-0">
                  <FileText className="h-5 w-5" />
                </div>
                <div className="min-w-0">
                  <p className="font-bold text-xs sm:text-sm text-gray-800 truncate">
                    {doc.filename || doc.project_title}
                  </p>
                  <p className="text-[11px] text-gray-400 mt-0.5">Views: {doc.view_count || 0}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 🔴 Section 2: Header Controls (Responsive Flex Direction) */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 sm:gap-4 mb-4">
        <h2 className="text-sm sm:text-base font-bold">All files</h2>
        
        {/* Action Buttons Group */}
        <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
          
          {/* Filter Dropdowns (ซ่อนบนมือถือ แสดงเฉพาะจอใหญ่ lg ขึ้นไป) */}
          <div className="hidden lg:flex items-center gap-2">
            {["Category", "Modified", "Years"].map((filter) => (
              <button 
                key={filter} 
                className="px-3 py-1.5 bg-gray-100 border border-gray-300 rounded-lg text-xs font-medium flex items-center gap-1.5"
              >
                <span>{filter}</span>
                <ChevronDown className="h-3 w-3 text-gray-500" />
              </button>
            ))}
          </div>

          {/* 🔵 ปุ่มลิงก์ไปหน้า Chat ( Responsive: ซ่อนตัวอักษรบนมือถือ ) */}
          <Link 
            to="/chat" 
            className="p-2 sm:px-3 sm:py-2 bg-white hover:bg-gray-100 border border-gray-300 text-gray-700 rounded-lg shadow-sm flex items-center gap-2 transition"
            title="ไปที่หน้า Chat"
          >
            <MessageSquare className="h-4 w-4 text-[#1D61E7]" />
            <span className="hidden sm:inline text-xs font-bold">Chat</span>
          </Link>

          {/* 🔵 ปุ่ม Upload file */}
          <button
            onClick={() => setIsUploadModalOpen(true)}
            className="px-3.5 py-2 bg-[#1D61E7] hover:bg-blue-700 text-white rounded-lg shadow-sm font-bold text-xs flex items-center gap-2 transition"
          >
            <Upload className="h-4 w-4" />
            <span className="inline text-xs">Upload file</span>
          </button>
        </div>
      </div>

      {/* 🔴 Section 3: Data Table (Responsive Table Scroll) */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        {/* overflow-x-auto ช่วยให้เลื่อนตารางซ้าย-ขวาได้บนจอมือถือไม่ให้หน้าจอเละ */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs sm:text-sm min-w-[650px]">
            <thead className="bg-[#EAEAEA] text-gray-700 font-bold border-b border-gray-300">
              <tr>
                <th className="py-3 px-4 sm:px-6">Title</th>
                <th className="py-3 px-4">Filename</th>
                <th className="py-3 px-4">Views</th>
                <th className="py-3 px-4 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading ? (
                <tr><td colSpan="4" className="text-center py-6">Loading documents...</td></tr>
              ) : documents.map((file) => (
                <tr key={file.document_id} className="hover:bg-gray-50/80 transition">
                  <td className="py-3.5 px-4 sm:px-6 font-semibold flex items-center gap-2.5 text-gray-800">
                    <FileText className="h-4 w-4 text-[#800000] shrink-0" />
                    <span className="truncate max-w-[180px] sm:max-w-xs">{file.project_title || "Untitled"}</span>
                  </td>
                  <td className="py-3.5 px-4 text-gray-600 truncate max-w-[150px]">{file.filename}</td>
                  <td className="py-3.5 px-4 text-gray-600">{file.view_count || 0}</td>
                  <td className="py-3.5 px-4 text-center relative">
                    <button 
                      onClick={() => setActiveMenuId(activeMenuId === file.document_id ? null : file.document_id)}
                      className="p-1 hover:bg-gray-200 rounded text-gray-500"
                    >
                      <MoreVertical className="h-4 w-4" />
                    </button>

                    {activeMenuId === file.document_id && (
                      <div className="absolute right-6 top-10 z-30 w-32 bg-white border border-gray-200 shadow-xl rounded-lg p-1 text-left">
                        <button 
                          onClick={() => handleDelete(file.document_id)} 
                          className="flex items-center gap-2 w-full px-3 py-1.5 text-xs text-red-600 hover:bg-red-50 rounded"
                        >
                          <Trash2 className="h-3.5 w-3.5" /> ลบไฟล์
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal Upload */}
      <UploadModal 
        isOpen={isUploadModalOpen} 
        onClose={() => setIsUploadModalOpen(false)} 
        onUploadSuccess={loadDocuments}
      />
    </div>
  );
}