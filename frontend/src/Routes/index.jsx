import { Routes, Route, Navigate } from 'react-router-dom';
import Chat from '../pages/Chat';
import Dashboard from '../pages/Dashboard';
import Documents from '../pages/Documents';
import Feedback from '../pages/Feedback';
import AIconfig from '../pages/AIconfig';

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/chat" replace />} />
      <Route path="/chat" element={<Chat />} />
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/documents" element={<Documents />} />
      <Route path="/feedback" element={<Feedback />} />
      <Route path="/ai-config" element={<AIconfig />} />
      <Route path="*" element={<Navigate to="/chat" replace />} />
    </Routes>
  );
}