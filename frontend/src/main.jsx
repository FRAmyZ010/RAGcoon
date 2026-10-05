import React, { useEffect } from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Link, Navigate, Route, Routes } from "react-router-dom";
import App from "./App.jsx";
import RequireAuth from "./components/RequireAuth.jsx";
import DocumentsManagement from "./pages/Documents.jsx";
import FeedbackPage from "./pages/Feedback.jsx";
import FeedbackAdmin from "./pages/FeedbackAdmin.jsx";
import LoginPage from "./pages/Login.jsx";
import Placeholder from "./pages/Placeholder.jsx";
import "./index.css";

let visitSent = false;

function MissingChat() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[#f4f1ea] px-6 text-slate-800">
      <div className="max-w-md rounded-3xl bg-white px-8 py-10 text-center shadow-lg">
        <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#800000]">404</p>
        <h1 className="mt-2 text-2xl font-semibold">Not Found</h1>
        <p className="mt-2 text-sm text-slate-500">ไม่พบแชทนี้ หรือคุณไม่มีสิทธิ์เปิดดู</p>
        <Link to="/chat" className="mt-6 inline-flex rounded-full bg-[#800000] px-5 py-2 text-sm font-semibold text-white">
          กลับไปแชทของคุณ
        </Link>
      </div>
    </div>
  );
}
function VisitTracker() {
  useEffect(() => {
    if (visitSent) return;
    visitSent = true;
    fetch("/api/v1/dashboard/track-visit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    }).catch(() => {});
  }, []);
  return null;
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <VisitTracker />
      <Routes>
        <Route path="/" element={<Navigate to="/chat" replace />} />
        <Route path="/chat" element={<App />} />
        <Route path="/chat/:chatId" element={<MissingChat />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/feedback" element={<FeedbackPage />} />
        <Route
          path="/feedback-admin"
          element={
            <RequireAuth>
              <FeedbackAdmin />
            </RequireAuth>
          }
        />
        <Route
          path="/documents"
          element={
            <RequireAuth>
              <DocumentsManagement />
            </RequireAuth>
          }
        />
        <Route path="/dashboard" element={<Placeholder title="Dashboard" />} />
        <Route path="*" element={<Navigate to="/chat" replace />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
