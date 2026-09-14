import React, { useState } from 'react';
import { X, UploadCloud, Loader2 } from 'lucide-react';

export default function UploadModal({ isOpen, onClose, onUploadSuccess }) {
  const [isUploading, setIsUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  if (!isOpen) return null;

  // ฟังก์ชันอัปโหลดไฟล์
  const handleUpload = async (file) => {
    if (!file) return;

    setIsUploading(true);
    try {
      // 1. เตรียม Data ส่งหา Backend
      const formData = new FormData();
      formData.append('file', file);

      // 2. ยิง API (ตัวอย่างการต่อ Backend)
      // await axios.post('/api/upload', formData);

      console.log('File uploaded:', file.name);

      // ส่ง callback กลับไปอัปเดตหน้าหลัก (ถ้ามี)
      if (onUploadSuccess) onUploadSuccess(file);
      
      onClose();
    } catch (error) {
      console.error('Upload failed:', error);
    } finally {
      setIsUploading(false);
    }
  };

  // รองรับการ Click เลือกไฟล์
  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleUpload(e.target.files[0]);
    }
  };

  // รองรับ Drag and Drop (ลากไฟล์มาวาง)
  const handleDrop = (e) => {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleUpload(e.dataTransfer.files[0]);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6 relative">
        <button 
          onClick={onClose}
          disabled={isUploading}
          className="absolute top-4 right-4 text-slate-400 hover:text-slate-600 disabled:opacity-50"
        >
          <X size={20} />
        </button>

        <h3 className="text-lg font-bold text-slate-800 mb-4">Upload File</h3>
        
        <label 
          onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
          onDragLeave={() => setDragActive(false)}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-xl p-8 flex flex-col items-center justify-center cursor-pointer transition ${
            dragActive ? 'border-blue-500 bg-blue-50' : 'border-slate-300 bg-slate-50 hover:bg-blue-50/50 hover:border-blue-500'
          }`}
        >
          {isUploading ? (
            <div className="flex flex-col items-center py-2">
              <Loader2 className="w-10 h-10 text-blue-500 animate-spin mb-2" />
              <p className="text-sm font-semibold text-slate-600">Uploading...</p>
            </div>
          ) : (
            <>
              <UploadCloud className="w-12 h-12 text-blue-500 mb-2" />
              <p className="text-sm font-semibold text-slate-700">Click to upload or drag and drop</p>
              <p className="text-xs text-slate-400 mt-1">PDF, DOCX, TXT (max. 10MB)</p>
            </>
          )}
          
          <input 
            type="file" 
            className="hidden" 
            onChange={handleFileChange}
            disabled={isUploading}
          />
        </label>
      </div>
    </div>
  );
}