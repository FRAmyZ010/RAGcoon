import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  Bell,
  Eye,
  FileText,
  FolderClosed,
  LayoutDashboard,
  LogOut,
  MessageSquare,
  Search,
} from "lucide-react";
import { clearAuth } from "../services/authApi";
import { fetchOverview } from "../services/dashboardApi";

const RANGES = [
  { days: 1, label: "1 day" },
  { days: 7, label: "7 days" },
  { days: 15, label: "15 days" },
  { days: 30, label: "1 month" },
];

const NAV = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/documents", label: "Documents", icon: FolderClosed },
  { to: "/feedback-admin", label: "Feedback", icon: MessageSquare },
  { to: "/chat", label: "Chat Workspace", icon: MessageSquare },
];

function localDay(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function recentSearches(rows, dayCount) {
  const counts = new Map((rows || []).map((row) => [String(row.day).slice(0, 10), row.count]));
  const points = [];
  for (let offset = dayCount - 1; offset >= 0; offset -= 1) {
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

function smoothLine(coords) {
  if (coords.length === 0) return "";
  if (coords.length === 1) return `M ${coords[0].x} ${coords[0].y}`;
  let path = `M ${coords[0].x} ${coords[0].y}`;
  for (let index = 0; index < coords.length - 1; index += 1) {
    const previous = coords[index === 0 ? index : index - 1];
    const current = coords[index];
    const next = coords[index + 1];
    const after = coords[index + 2] || next;
    const control1x = current.x + (next.x - previous.x) / 6;
    const control1y = current.y + (next.y - previous.y) / 6;
    const control2x = next.x - (after.x - current.x) / 6;
    const control2y = next.y - (after.y - current.y) / 6;
    path += ` C ${control1x} ${control1y}, ${control2x} ${control2y}, ${next.x} ${next.y}`;
  }
  return path;
}

function SearchChart({ points }) {
  const width = 640;
  const height = 220;
  const padL = 36;
  const padR = 12;
  const padT = 12;
  const padB = 28;
  const max = Math.max(1, ...points.map((point) => point.count));
  const innerW = width - padL - padR;
  const innerH = height - padT - padB;
  const baseline = padT + innerH;
  const ticks = [...new Set([0, Math.ceil(max / 2), max])];
  const labelEvery = points.length > 20 ? 5 : points.length > 10 ? 2 : 1;
  const coords = points.map((point, index) => {
    const x = points.length <= 1 ? padL + innerW / 2 : padL + (index / (points.length - 1)) * innerW;
    const y = baseline - (point.count / max) * innerH;
    return { ...point, x, y };
  });
  const line = smoothLine(coords);
  const area = coords.length
    ? `${line} L ${coords[coords.length - 1].x} ${baseline} L ${coords[0].x} ${baseline} Z`
    : "";

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="h-full w-full" role="img" aria-label="Search activity">
      <defs>
        <linearGradient id="searchActivityFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#6d9478" stopOpacity="0.38" />
          <stop offset="100%" stopColor="#6d9478" stopOpacity="0" />
        </linearGradient>
      </defs>
      {ticks.map((tick) => {
        const y = baseline - (tick / max) * innerH;
        return (
          <text key={tick} x={padL - 8} y={y + 3} textAnchor="end" fontSize="11" fill="#9ca3af">
            {tick}
          </text>
        );
      })}
      {area && <path d={area} fill="url(#searchActivityFill)" />}
      {line && (
        <path d={line} fill="none" stroke="#5f8a6e" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      )}
      {coords.map((point, index) =>
        index % labelEvery === 0 ? (
          <text key={point.day} x={point.x} y={height - 8} textAnchor="middle" fontSize="11" fill="#9ca3af">
            {point.label}
          </text>
        ) : null
      )}
    </svg>
  );
}

function Panel({ title, hint, action, children }) {
  return (
    <section className="flex min-h-[240px] flex-col rounded-xl bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-bold text-gray-900">{title}</h2>
          <p className="text-[11px] text-gray-500">{hint}</p>
        </div>
        {action}
      </div>
      <div className="min-h-0 flex-1">{children}</div>
    </section>
  );
}

export default function Dashboard() {
  const navigate = useNavigate();
  const location = useLocation();
  const displayName = localStorage.getItem("username") || "Admin";
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [rangeDays, setRangeDays] = useState(7);
  const [query, setQuery] = useState("");
  const [overview, setOverview] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [chartLoading, setChartLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setChartLoading(true);
    fetchOverview(rangeDays)
      .then((data) => {
        if (!cancelled) setOverview(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || "โหลด Dashboard ไม่สำเร็จ");
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
          setChartLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [rangeDays]);

  const rangeLabel = RANGES.find((item) => item.days === rangeDays)?.label ?? "7 days";
  const searches = useMemo(
    () => recentSearches(overview?.searches_by_day, rangeDays),
    [overview, rangeDays]
  );
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
    { title: "Total Document", count: overview?.total_documents ?? 0, note: overview ? `${overview.total_projects} projects` : "", icon: FileText },
    { title: "Search Today", count: searchToday, note: "today", icon: Search },
    { title: "Visits", count: overview?.total_visits ?? 0, note: "all visits", icon: Eye },
    { title: "Feedback", count: overview?.total_feedbacks ?? 0, note: "all notes", icon: MessageSquare },
  ];

  const logout = () => {
    clearAuth();
    navigate("/login", { replace: true });
  };

  return (
    <div className="relative flex h-screen w-screen overflow-hidden bg-gray-100 font-sans text-xs text-gray-800 sm:text-sm">
      {sidebarOpen && (
        <button
          type="button"
          aria-label="Close menu"
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
              type="button"
              onClick={() => setSidebarOpen(false)}
              className="text-gray-400 hover:text-white lg:hidden"
            >
              ✕
            </button>
          </div>
          <nav className="space-y-1">
            {NAV.map((item) => {
              const active = location.pathname === item.to;
              const Icon = item.icon;
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  onClick={() => setSidebarOpen(false)}
                  className={`flex items-center gap-2.5 rounded-lg px-2.5 py-1.5 ${
                    active ? "bg-white font-bold text-gray-900" : "text-gray-300 hover:bg-white/10"
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>
        <button
          type="button"
          onClick={logout}
          className="flex w-full items-center justify-between rounded-lg bg-white px-2.5 py-1.5 font-bold text-gray-900 hover:bg-gray-200"
        >
          <span>Log Out</span>
          <LogOut className="h-3.5 w-3.5" />
        </button>
      </aside>

      <main className="min-w-0 flex-1 overflow-y-auto p-3 sm:p-4 lg:p-5">
        <header className="mb-4 flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={() => setSidebarOpen(true)}
            className="rounded-lg bg-white p-1.5 shadow-sm hover:bg-gray-50 lg:hidden"
          >
            ☰
          </button>
          <div className="min-w-0">
            <h1 className="text-base font-bold text-gray-900 sm:text-lg">Overview</h1>
            <p className="text-[11px] text-gray-500 sm:text-xs">ตัวเลขจากคลังเอกสาร การค้นหา และการเข้าชม</p>
          </div>
          <div className="ml-auto flex items-center gap-2.5">
            <div className="relative hidden sm:block">
              <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search"
                className="h-8 w-44 rounded-lg border border-gray-200 bg-white pl-8 pr-3 text-xs text-gray-800 shadow-sm outline-none focus:ring-2 focus:ring-[#800000]/30"
              />
            </div>
            <Bell className="h-4 w-4 text-gray-600" />
            <div className="flex items-center gap-2">
              <div className="flex h-6 w-6 items-center justify-center rounded-full bg-[#800000] text-[10px] font-bold text-white">
                {displayName.slice(0, 2).toUpperCase()}
              </div>
              <span className="hidden text-sm font-bold text-gray-800 sm:inline">{displayName}</span>
            </div>
          </div>
        </header>

        {error && (
          <p className="mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-red-700" role="alert">
            {error}
          </p>
        )}

        <section className="mb-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
          {cards.map((card) => {
            const Icon = card.icon;
            return (
              <article key={card.title} className="rounded-xl bg-white p-3.5 shadow-sm">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <span className="text-[11px] font-medium text-gray-500 sm:text-xs">{card.title}</span>
                  <span className="rounded-md bg-[#800000]/10 p-1 text-[#800000]">
                    <Icon className="h-3.5 w-3.5" />
                  </span>
                </div>
                <p className="text-2xl font-bold leading-none text-gray-900">{loading ? "…" : card.count}</p>
                {card.note && <p className="mt-1.5 text-[11px] text-gray-400">{card.note}</p>}
              </article>
            );
          })}
        </section>

        <section className="grid grid-cols-1 gap-3 xl:grid-cols-2">
          <Panel
            title="Search Activity"
            hint={`จำนวนคำถามรายวัน ใน ${rangeLabel}`}
            action={
              <div className="flex shrink-0 rounded-lg bg-gray-100 p-0.5">
                {RANGES.map((item) => (
                  <button
                    key={item.days}
                    type="button"
                    onClick={() => setRangeDays(item.days)}
                    className={`rounded-md px-2 py-1 text-[11px] font-semibold ${
                      rangeDays === item.days ? "bg-[#5f8a6e] text-white" : "text-gray-600 hover:bg-white"
                    }`}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            }
          >
            {loading || chartLoading ? (
              <p className="text-xs text-gray-500">Loading...</p>
            ) : (
              <div className="h-52">
                <SearchChart points={searches} />
              </div>
            )}
          </Panel>

          <Panel title="Documents by years" hint="จำนวนเอกสารทั้งหมด ตามปีการศึกษา">
            {years.length === 0 ? (
              <p className="text-xs text-gray-500">{loading ? "Loading..." : "ยังไม่มีเอกสาร"}</p>
            ) : (
              <div className="flex h-44 items-end gap-3 px-2">
                {years.map((row) => (
                  <div key={row.year ?? "unknown"} className="flex h-full min-w-0 flex-1 flex-col items-center justify-end">
                    <span className="mb-1 text-[11px] font-bold text-gray-600">{row.count}</span>
                    <div className="flex w-full flex-1 items-end justify-center">
                      <div
                        className="w-8 rounded-t-lg bg-gradient-to-t from-[#5f8a6e] to-[#d7e6da]"
                        style={{ height: `${Math.max(10, (row.count / yearMax) * 100)}%` }}
                      />
                    </div>
                    <span className="mt-2 text-[11px] font-semibold text-gray-700">{row.year ?? "—"}</span>
                  </div>
                ))}
              </div>
            )}
          </Panel>

          <Panel title="Top Keywords" hint="คำที่พบบ่อยในเอกสารทั้งหมด">
            <div className="flex max-h-52 flex-col gap-2.5 overflow-y-auto pr-1">
              {keywords.length === 0 && (
                <p className="text-xs text-gray-500">{loading ? "Loading..." : "ยังไม่มี keyword"}</p>
              )}
              {keywords.map((item, index) => (
                <div key={item.keyword} className="grid grid-cols-[minmax(0,9rem)_1fr_1.5rem] items-center gap-3">
                  <span className="truncate text-xs font-semibold text-gray-800">{item.keyword}</span>
                  <div className="h-2.5 overflow-hidden rounded-full bg-gray-100">
                    <div
                      className="h-full rounded-full bg-[#6d9478]"
                      style={{ width: `${Math.max(8, (item.count / keywordMax) * 100)}%`, opacity: index === 0 ? 1 : 0.72 }}
                    />
                  </div>
                  <span className="text-right text-xs font-bold text-gray-800">{item.count}</span>
                </div>
              ))}
            </div>
          </Panel>

          <Panel title="Most Viewed Documents" hint="เอกสารที่ถูกเปิดดูมากสุดทั้งหมด">
            <div className="flex max-h-52 flex-col gap-2 overflow-y-auto pr-1">
              {viewed.length === 0 && (
                <p className="text-xs text-gray-500">{loading ? "Loading..." : "ยังไม่มีเอกสารที่ถูกเปิด"}</p>
              )}
              {viewed.map((doc, index) => (
                <div key={doc.document_id} className="flex items-center gap-3 rounded-lg px-1 py-1.5 hover:bg-gray-50">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#5f8a6e]/15 text-[11px] font-bold text-[#4f735c]">
                    {index + 1}
                  </span>
                  <span className="min-w-0 flex-1 truncate text-xs font-semibold text-gray-800">
                    {doc.title || doc.filename}
                  </span>
                  <span className="text-xs font-bold text-gray-700">{doc.view_count}</span>
                </div>
              ))}
            </div>
          </Panel>
        </section>
      </main>
    </div>
  );
}
