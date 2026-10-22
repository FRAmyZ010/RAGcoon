// src/components/ui/UploadModal.jsx
import React, { useState } from "react";
import { X, UploadCloud } from "lucide-react";
import { uploadDocumentApi } from "../../services/api";

export default function UploadModal({ isOpen, onClose, onUploadSuccess }) {
  const [file, setFile] = useState(null);
  const [formData, setFormData] = useState({
    project_title: "",
    academic_year: 2024,
    authors: "",
    advisor: "",
  });
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return alert("กรุณาเลือกไฟล์ PDF ก่อนครับ");

    try {
      setLoading(true);
      await uploadDocumentApi(file, formData);
      alert("อัปโหลดเอกสารเข้าสู่ระบบสำเร็จ!");
      if (onUploadSuccess) onUploadSuccess();
      onClose();
    } catch (err) {
      alert("เกิดข้อผิดพลาดในการอัปโหลดไฟล์");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-xl p-6 max-w-md w-full shadow-2xl font-mono text-xs text-[#353535]">
        <div className="flex justify-between items-center border-b pb-3 mb-4">
          <h3 className="font-bold text-sm">Upload Senior Project PDF</h3>
          <button onClick={onClose} className="p-1 text-gray-400 hover:text-gray-600">
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={handleUpload} className="space-y-3">
          <div>
            <label className="block font-bold mb-1">Project Title</label>
            <input
              type="text"
              name="project_title"
              required
              placeholder="ชื่อโครงงาน"
              className="w-full p-2 border rounded-md"
              onChange={handleChange}
            />
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block font-bold mb-1">Academic Year</label>
              <input
                type="number"
                name="academic_year"
                defaultValue={2024}
                className="w-full p-2 border rounded-md"
                onChange={handleChange}
              />
            </div>
            <div>
              <label className="block font-bold mb-1">Advisor</label>
              <input
                type="text"
                name="advisor"
                placeholder="ชื่ออาจารย์ที่ปรึกษา"
                className="w-full p-2 border rounded-md"
                onChange={handleChange}
              />
            </div>
          </div>

          <div>
            <label className="block font-bold mb-1">Authors</label>
            <input
              type="text"
              name="authors"
              placeholder="ชื่อผู้จัดทำ"
              className="w-full p-2 border rounded-md"
              onChange={handleChange}
            />
          </div>

          <div className="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center bg-gray-50 mt-2">
            <UploadCloud className="h-6 w-6 mx-auto text-blue-500 mb-1" />
            <input
              type="file"
              accept=".pdf"
              required
              onChange={(e) => setFile(e.target.files[0])}
              className="w-full text-xs text-gray-500 file:mr-2 file:py-1 file:px-3 file:rounded-md file:border-0 file:bg-blue-50 file:text-blue-700"
            />
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border rounded-lg hover:bg-gray-100"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 bg-[#1D61E7] text-white rounded-lg font-bold hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? "Ingesting PDF..." : "Upload"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}