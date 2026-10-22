import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  FolderClosed,
  LayoutDashboard,
  LogOut,
  MessageSquare,
  Bell,
} from "lucide-react";
import { clearAuth } from "../services/authApi";
import {
  downloadFeedbackFile,
  listFeedback,
  updateFeedbackStatus,
} from "../services/feedbackApi";

const TYPES = ["All", "Suggestion", "Bug", "Others"];
const STATUSES = ["All", "Open", "In Progress", "Resolved"];

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function statusClass(status) {
  if (status === "In Progress") return "bg-amber-100 text-amber-800";
  if (status === "Resolved") return "bg-emerald-100 text-emerald-800";
  return "bg-rose-100 text-rose-800";
}

export default function FeedbackAdmin() {
  const navigate = useNavigate();
  const displayName = localStorage.getItem("username") || "Admin";
  const [rows, setRows] = useState([]);
  const [feedbackType, setFeedbackType] = useState("All");
  const [status, setStatus] = useState("All");
  const [q, setQ] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const load = useCallback(async () => {
    setError("");
    try {
      const data = await listFeedback({ feedbackType, status, q });
      setRows(data);
    } catch (err) {
      setError(err.message || "โหลด Feedback ไม่สำเร็จ");
    } finally {
      setLoading(false);
    }
  }, [feedbackType, status, q]);

  useEffect(() => {
    setLoading(true);
    const timer = setTimeout(load, 250);
    return () => clearTimeout(timer);
  }, [load]);

  const changeStatus = async (id, nextStatus) => {
    setError("");
    try {
      await updateFeedbackStatus(id, nextStatus);
      await load();
    } catch (err) {
      setError(err.message || "อัปเดตสถานะไม่สำเร็จ");
    }
  };

  return (
    <div className="relative flex h-screen w-screen overflow-hidden bg-gray-100 font-sans text-xs text-gray-800 sm:text-sm">
      {sidebarOpen && (
        <div
          onClick={() => setSidebarOpen(false)}
          className="fixed inset-0 z-30 bg-black/50 lg:hidden"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-56 shrink-0 flex-col justify-between bg-[#2d2d2d] p-3 text-white transition-transform duration-300 lg:static ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        }`}
      >
        <div>
          <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-bold sm:text-base">
              <span className="text-lg">🦝</span>
              <span>RAGcoon</span>
            </div>
            <button
              onClick={() => setSidebarOpen(false)}
              className="text-gray-400 hover:text-white lg:hidden"
            >
              ✕
            </button>
          </div>
          <nav className="space-y-1">
            <Link to="/dashboard" className="flex items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-gray-300 hover:bg-white/10">
              <LayoutDashboard className="h-3.5 w-3.5" />
              <span>Dashboard</span>
            </Link>
            <Link to="/documents" className="flex items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-gray-300 hover:bg-white/10">
              <FolderClosed className="h-3.5 w-3.5" />
              <span>Documents</span>
            </Link>
            <Link to="/feedback-admin" className="flex items-center gap-2.5 rounded-lg bg-white px-2.5 py-1.5 font-bold text-gray-900">
              <MessageSquare className="h-3.5 w-3.5" />
              <span>Feedback</span>
            </Link>
            <Link to="/chat" className="flex items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-gray-300 hover:bg-white/10">
              <MessageSquare className="h-3.5 w-3.5" />
              <span>Chat Workspace</span>
            </Link>
          </nav>
        </div>
        <button
          type="button"
          onClick={() => {
            clearAuth();
            navigate("/login", { replace: true });
          }}
          className="flex w-full items-center justify-between rounded-lg bg-white px-2.5 py-1.5 font-bold text-gray-900 hover:bg-gray-200"
        >
          <span>Log Out</span>
          <LogOut className="h-3.5 w-3.5" />
        </button>
      </aside>

      <main className="min-w-0 flex-1 overflow-y-auto p-3 sm:p-4 lg:p-5">
        <header className="mb-4 flex items-center justify-between">
          <button
            onClick={() => setSidebarOpen(true)}
            className="rounded-lg bg-white p-1.5 shadow-sm hover:bg-gray-50 lg:hidden"
          >
            ☰
          </button>
          <div className="ml-auto flex items-center gap-2.5">
            <Bell className="h-4 w-4 text-gray-600" />
            <span className="hidden text-sm font-bold text-gray-800 sm:inline">{displayName}</span>
          </div>
        </header>

        <div className="mb-4">
          <h1 className="text-base font-bold text-gray-900 sm:text-lg">Feedback</h1>
          <p className="text-[11px] text-gray-500 sm:text-xs">{rows.length} รายการ</p>
        </div>

        <div className="mb-4 flex flex-col gap-2 sm:flex-row">
          <input
            value={q}
            onChange={(event) => setQ(event.target.value)}
            placeholder="Search..."
            className="h-9 flex-1 rounded-lg border border-gray-300 bg-white px-3"
          />
          <select
            value={feedbackType}
            onChange={(event) => setFeedbackType(event.target.value)}
            className="h-9 rounded-lg border border-gray-300 bg-white px-2"
          >
            {TYPES.map((item) => (
              <option key={item} value={item}>
                Type: {item}
              </option>
            ))}
          </select>
          <select
            value={status}
            onChange={(event) => setStatus(event.target.value)}
            className="h-9 rounded-lg border border-gray-300 bg-white px-2"
          >
            {STATUSES.map((item) => (
              <option key={item} value={item}>
                Status: {item}
              </option>
            ))}
          </select>
        </div>

        {error && (
          <div className="mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-red-700">{error}</div>
        )}

        <div className="overflow-x-auto rounded-xl bg-white shadow-sm">
          <table className="w-full min-w-[720px] text-left">
            <thead>
              <tr className="border-b bg-gray-50 text-[11px] uppercase text-gray-500">
                <th className="px-3 py-3">Name</th>
                <th className="px-3 py-3">Feedback</th>
                <th className="px-3 py-3">Type</th>
                <th className="px-3 py-3">File</th>
                <th className="px-3 py-3">Status</th>
                <th className="px-3 py-3">Date</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td colSpan={6} className="px-3 py-8 text-center text-gray-500">
                    Loading...
                  </td>
                </tr>
              )}
              {!loading && rows.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-3 py-8 text-center text-gray-500">
                    ยังไม่มี Feedback
                  </td>
                </tr>
              )}
              {!loading &&
                rows.map((row) => (
                  <tr key={row.id} className="border-b last:border-none">
                    <td className="px-3 py-3 font-semibold">{row.submitter_name || "—"}</td>
                    <td className="max-w-xs px-3 py-3">{row.comment}</td>
                    <td className="px-3 py-3">{row.feedback_type}</td>
                    <td className="px-3 py-3">
                      {row.attachment_name ? (
                        <button
                          type="button"
                          onClick={() => downloadFeedbackFile(row.id, row.attachment_name).catch((err) => setError(err.message))}
                          className="text-left font-semibold text-[#800000] hover:underline"
                        >
                          {row.attachment_name}
                        </button>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="px-3 py-3">
                      <select
                        value={row.status}
                        onChange={(event) => changeStatus(row.id, event.target.value)}
                        className={`rounded-full px-2 py-1 text-[11px] font-bold ${statusClass(row.status)}`}
                      >
                        {STATUSES.filter((item) => item !== "All").map((item) => (
                          <option key={item} value={item}>
                            {item}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="whitespace-nowrap px-3 py-3 text-gray-500">{formatDate(row.created_at)}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
