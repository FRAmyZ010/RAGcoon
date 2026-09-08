import { X, UploadCloud } from 'lucide-react';

export default function UploadModal({ isOpen, onClose }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 font-mono">
      <div className="bg-white rounded-xl w-full max-w-md p-6 relative shadow-2xl">
        <button onClick={onClose} className="absolute right-4 top-4 text-gray-400 hover:text-black">
          <X size={18} />
        </button>
        
        <h3 className="text-xs font-bold text-gray-800 mb-4">Upload New Document</h3>
        
        <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 flex flex-col items-center justify-center gap-2 hover:border-blue-500 cursor-pointer bg-gray-50 transition-colors">
          <UploadCloud size={32} className="text-gray-400" />
          <p className="text-xs font-semibold text-gray-600">Click to upload or drag & drop</p>
          <p className="text-[10px] text-gray-400">PDF, TXT, DOCX up to 10MB</p>
        </div>

        <div className="flex justify-end gap-2 mt-6">
          <button onClick={onClose} className="px-4 py-2 text-xs font-semibold text-gray-600 hover:bg-gray-100 rounded-lg">
            Cancel
          </button>
          <button onClick={onClose} className="px-4 py-2 text-xs font-bold bg-[#2563EB] text-white rounded-lg hover:bg-blue-700">
            Upload
          </button>
        </div>
      </div>
    </div>
  );
}