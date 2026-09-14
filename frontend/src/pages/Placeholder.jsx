import { Link } from "react-router-dom";

export default function Placeholder({ title }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-100 p-6">
      <div className="max-w-md rounded-2xl border border-gray-200 bg-white p-8 text-center shadow-sm">
        <div className="mb-3 text-3xl">🦝</div>
        <h1 className="text-lg font-bold text-gray-900">{title}</h1>
        <p className="mt-2 text-sm text-gray-500">
          หน้านี้อยู่ในแผน Sprint ถัดไป ยังไม่ได้พัฒนา
        </p>
        <div className="mt-6 flex justify-center gap-3 text-sm">
          <Link
            to="/chat"
            className="rounded-lg bg-[#2d2d2d] px-4 py-2 font-semibold text-white hover:bg-black"
          >
            Chat
          </Link>
          <Link
            to="/documents"
            className="rounded-lg border border-gray-300 px-4 py-2 font-semibold text-gray-700 hover:bg-gray-50"
          >
            Documents
          </Link>
        </div>
      </div>
    </div>
  );
}
