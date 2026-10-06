import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  Bell,
  Calendar,
  ChevronLeft,
  ChevronRight,
  FolderKanban,
  LayoutDashboard,
  LogOut,
  Menu,
  MessageSquare,
  Search,
  MessageSquareQuote,
  PieChart,
  X,
} from "lucide-react";
import { clearAuth } from "../services/authApi";
import { fetchOverview } from "../services/dashboardApi";

const NAV = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/documents", label: "Documents", icon: FolderKanban },
  { to: "/feedback-admin", label: "Feedback", icon: MessageSquareQuote },
  { to: "/chat", label: "Chat Workspace", icon: MessageSquare },
];

function localDay(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function recentSearches(rows) {
  const counts = new Map((rows || []).map((row) => [String(row.day).slice(0, 10), row.count]));
  const points = [];
  for (let offset = 13; offset >= 0; offset -= 1) {
    const date = new Date();
    date.setHours(12, 0, 0, 0);
    date.setDate(date.getDate() - offset);
    const day = localDay(date);
    points.push({
      day,
      label: `${date.getDate()}`,
      count: counts.get(day) || 0,
    });
  }
  return points;
}

function SearchChart({ points }) {
  const width = 320;
  const height = 110;
  const max = Math.max(1, ...points.map((point) => point.count));
  const step = points.length > 1 ? width / (points.length - 1) : width;
  const coords = points.map((point, index) => {
    const x = index * step;
    const y = height - 8 - (point.count / max) * (height - 16);
    return `${x},${y}`;
  });
  const line = coords.join(" ");
  const area = `0,${height} ${line} ${width},${height}`;

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <svg viewBox={`0 0 ${width} ${height}`} className="h-full w-full" preserveAspectRatio="none" role="img" aria-label="Search activity">
        <polygon points={area} fill="#4b5563" opacity="0.15" />
        <polyline points={line} fill="none" stroke="#374151" strokeWidth="2" vectorEffect="non-scaling-stroke" />
      </svg>
      <div className="mt-1 flex justify-between font-mono text-[9px] text-neutral-400">
        {points.map((point) => (
          <span key={point.day}>{point.label}</span>
        ))}
      </div>
    </div>
  );
}

export default function Dashboard() {
  const navigate = useNavigate();
  const location = useLocation();
  const displayName = localStorage.getItem("username") || "Admin";
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [overview, setOverview] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    fetchOverview()
      .then((data) => {
        if (!cancelled) setOverview(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || "โหลด Dashboard ไม่สำเร็จ");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const searches = useMemo(() => recentSearches(overview?.searches_by_day), [overview]);
  const searchToday = searches.at(-1)?.count ?? 0;
  const years = useMemo(() => {
    const rows = [...(overview?.documents_by_year || [])];
    rows.sort((a, b) => (a.year ?? 9999) - (b.year ?? 9999));
    return rows;
  }, [overview]);
  const yearMax = Math.max(1, ...years.map((row) => row.count));
  const needle = query.trim().toLowerCase();
  const keywords = (overview?.top_keywords || []).filter((item) =>
    item.keyword.toLowerCase().includes(needle)
  );
  const keywordMax = Math.max(1, ...keywords.map((item) => item.count));
  const viewed = (overview?.most_viewed || []).filter((item) => {
    const label = `${item.title || ""} ${item.filename || ""}`.toLowerCase();
    return label.includes(needle);
  });

  const cards = [
    { title: "Total Document", count: overview?.total_documents ?? 0 },
    { title: "Search Today", count: searchToday },
    { title: "Visits", count: overview?.total_visits ?? 0 },
    { title: "Feedback", count: overview?.total_feedbacks ?? 0 },
  ];

  const logout = () => {
    clearAuth();
    navigate("/login", { replace: true });
  };

  return (
    <div className="flex h-screen w-screen select-none flex-col overflow-hidden bg-[#b2b5b8] font-sans text-slate-800 antialiased md:flex-row md:gap-3 md:p-3">
      {mobileOpen && (
        <button
          type="button"
          aria-label="Close menu"
          className="fixed inset-0 z-40 bg-black/40 md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <div className="z-40 flex shrink-0 items-center justify-between bg-[#2d2e30] p-3 text-white shadow-md md:hidden">
        <span className="font-mono text-lg font-bold">RAGcoon</span>
        <button type="button" onClick={() => setMobileOpen((open) => !open)} className="p-1.5 text-gray-300">
          {mobileOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      <aside
        className={`fixed inset-y-0 left-0 z-50 flex h-full shrink-0 flex-col justify-between overflow-hidden bg-[#2b2b2b] p-3.5 text-white shadow-xl transition-all duration-300 md:relative md:rounded-2xl ${
          collapsed ? "md:w-16" : "md:w-56"
        } ${mobileOpen ? "w-56 translate-x-0" : "-translate-x-full md:translate-x-0"}`}
      >
        <div className="flex flex-col gap-5">
          <div className="flex items-center justify-between px-0.5 pt-0.5">
            <span className={`font-mono text-lg font-bold ${collapsed && !mobileOpen ? "md:hidden" : ""}`}>RAGcoon</span>
            <button
              type="button"
              onClick={() => setCollapsed((value) => !value)}
              className="hidden rounded-md p-1 text-gray-400 hover:bg-neutral-800 hover:text-white md:flex"
            >
              {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
            </button>
          </div>
          <nav className="space-y-1.5">
            {NAV.map((item) => {
              const active = location.pathname === item.to;
              const Icon = item.icon;
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  onClick={() => setMobileOpen(false)}
                  className={`flex w-full items-center gap-3 rounded-xl px-3 py-2 text-xs font-medium transition-all ${
                    active ? "bg-white font-semibold text-black shadow-sm" : "text-gray-300 hover:bg-neutral-800 hover:text-white"
                  }`}
                >
                  <Icon size={16} className={active ? "text-black" : "text-gray-300"} />
                  {(!collapsed || mobileOpen) && <span className="truncate">{item.label}</span>}
                </Link>
              );
            })}
          </nav>
        </div>
        <div className="border-t border-neutral-700/50 pt-2">
          <button
            type="button"
            onClick={logout}
            className={`flex w-full items-center rounded-xl bg-neutral-100 py-2 font-mono font-medium text-black shadow-sm hover:bg-neutral-200 ${
              collapsed && !mobileOpen ? "justify-center px-0" : "justify-between px-3"
            }`}
          >
            {(!collapsed || mobileOpen) && <span className="text-xs">Log Out</span>}
            <LogOut size={15} />
          </button>
        </div>
      </aside>

      <main className="flex h-full min-h-0 flex-1 flex-col justify-between gap-3 overflow-hidden bg-[#bec1c4] p-3 md:rounded-2xl md:p-4">
        <header className="flex shrink-0 flex-col items-center justify-between gap-2 sm:flex-row">
          <h1 className="font-mono text-xl font-bold tracking-tight text-neutral-900">Overview</h1>
          <div className="flex w-full items-center justify-end gap-2.5 sm:w-auto">
            <div className="relative flex-1 sm:w-48">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" size={14} />
              <input
                type="text"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search"
                className="w-full rounded-lg border-none bg-white py-1 pl-8 pr-3 font-mono text-xs text-gray-800 shadow-sm focus:outline-none focus:ring-2 focus:ring-neutral-400"
              />
            </div>
            <Bell size={16} className="text-neutral-800" />
            <div className="flex items-center gap-1.5 px-1">
              <div className="flex h-6 w-6 items-center justify-center rounded-full bg-red-600 text-[10px] font-bold text-white shadow-sm">
                {displayName.slice(0, 1).toUpperCase()}
              </div>
              <span className="hidden whitespace-nowrap font-mono text-[11px] font-medium text-neutral-800 lg:inline">
                {displayName}
              </span>
            </div>
            <div className="flex items-center gap-1.5 rounded-lg border border-neutral-200/80 bg-white px-2.5 py-1 font-mono text-[11px] text-neutral-700 shadow-sm">
              <Calendar size={13} className="text-neutral-500" />
              <span className="whitespace-nowrap">14 days</span>
            </div>
          </div>
        </header>

        {error && (
          <p className="shrink-0 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
            {error}
          </p>
        )}

        <section className="grid shrink-0 grid-cols-2 gap-2.5 lg:grid-cols-4">
          {cards.map((card) => (
            <div key={card.title} className="flex flex-col justify-between rounded-xl border border-neutral-100 bg-white p-2.5 shadow-sm">
              <div className="mb-1 flex items-center justify-between">
                <span className="truncate font-mono text-[11px] font-medium text-neutral-500">{card.title}</span>
                <div className="shrink-0 rounded-md bg-purple-100 p-1 text-purple-600">
                  <PieChart size={13} />
                </div>
              </div>
              <div className="font-mono text-xl font-bold leading-tight text-neutral-900">
                {loading ? "…" : card.count}
              </div>
            </div>
          ))}
        </section>

        <section className="grid min-h-0 flex-1 grid-cols-1 gap-2.5 lg:grid-cols-2">
          <div className="flex min-h-0 flex-col overflow-hidden rounded-xl border border-neutral-100 bg-white p-3 shadow-sm">
            <h3 className="mb-1 shrink-0 font-mono text-[11px] font-bold tracking-wide text-neutral-800">Search Activity</h3>
            {loading ? <p className="text-xs text-neutral-500">Loading...</p> : <SearchChart points={searches} />}
          </div>

          <div className="flex min-h-0 flex-col overflow-hidden rounded-xl border border-neutral-100 bg-white p-3 shadow-sm">
            <h3 className="mb-2 shrink-0 font-mono text-[11px] font-bold tracking-wide text-neutral-800">Documents by years</h3>
            {years.length === 0 ? (
              <p className="text-xs text-neutral-500">{loading ? "Loading..." : "ยังไม่มีเอกสาร"}</p>
            ) : (
              <div className="flex min-h-0 flex-1 items-end gap-2">
                {years.map((row) => (
                  <div key={row.year ?? "unknown"} className="flex h-full min-w-0 flex-1 flex-col items-center justify-end">
                    <span className="mb-1 font-mono text-[10px] font-bold text-neutral-700">{row.count}</span>
                    <div
                      className="w-full max-w-6 rounded-md bg-[#c4c4c4]"
                      style={{ height: `${Math.max(8, (row.count / yearMax) * 100)}%` }}
                    />
                    <span className="mt-1 font-mono text-[10px] font-bold text-neutral-800">{row.year ?? "—"}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="flex min-h-0 flex-col overflow-hidden rounded-xl border border-neutral-100 bg-white p-3 shadow-sm">
            <h3 className="mb-2 shrink-0 font-mono text-[11px] font-bold tracking-wide text-neutral-800">Top Keywords</h3>
            <div className="flex min-h-0 flex-1 flex-col justify-around overflow-auto">
              {keywords.length === 0 && (
                <p className="text-xs text-neutral-500">{loading ? "Loading..." : "ยังไม่มี keyword"}</p>
              )}
              {keywords.map((item) => (
                <div key={item.keyword} className="flex items-center gap-3 font-mono text-[11px]">
                  <span className="w-20 truncate font-bold text-neutral-800">{item.keyword}</span>
                  <div className="flex h-4 flex-1 items-center overflow-hidden rounded-sm bg-neutral-100 p-0.5">
                    <div className="h-full rounded-sm bg-black" style={{ width: `${(item.count / keywordMax) * 100}%` }} />
                  </div>
                  <span className="w-6 text-right font-bold text-neutral-800">{item.count}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="flex min-h-0 flex-col overflow-hidden rounded-xl border border-neutral-100 bg-white p-3 shadow-sm">
            <h3 className="mb-2 shrink-0 font-mono text-[11px] font-bold tracking-wide text-neutral-800">Most Viewed Documents</h3>
            <div className="flex min-h-0 flex-1 flex-col justify-around overflow-auto">
              {viewed.length === 0 && (
                <p className="text-xs text-neutral-500">{loading ? "Loading..." : "ยังไม่มีเอกสารที่ถูกเปิด"}</p>
              )}
              {viewed.map((doc) => (
                <div key={doc.document_id} className="flex items-center justify-between rounded px-1 py-0.5 font-mono text-[11px]">
                  <span className="max-w-[85%] truncate font-bold text-neutral-800">{doc.title || doc.filename}</span>
                  <span className="font-bold text-neutral-800">{doc.view_count}</span>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
