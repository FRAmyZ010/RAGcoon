import React, { useEffect } from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import App from "./App.jsx";
import RequireAuth from "./components/RequireAuth.jsx";
import DocumentsManagement from "./pages/Documents.jsx";
import FeedbackPage from "./pages/Feedback.jsx";
import FeedbackAdmin from "./pages/FeedbackAdmin.jsx";
import LoginPage from "./pages/Login.jsx";
import Placeholder from "./pages/Placeholder.jsx";
import "./index.css";

let visitSent = false;

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
