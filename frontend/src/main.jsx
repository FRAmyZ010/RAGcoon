import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import App from "./App.jsx";
import RequireAuth from "./components/RequireAuth.jsx";
import DocumentsManagement from "./pages/Documents.jsx";
import LoginPage from "./pages/Login.jsx";
import Placeholder from "./pages/Placeholder.jsx";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/chat" replace />} />
        <Route path="/chat" element={<App />} />
        <Route path="/login" element={<LoginPage />} />
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
