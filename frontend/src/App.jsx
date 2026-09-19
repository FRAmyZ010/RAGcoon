import React, { useState } from 'react';
import { 
  Home, 
  Folder, 
  MessageSquare, 
  LogOut, 
  Search, 
  Bell, 
  Calendar, 
  Eye, 
  EyeOff, 
  ArrowRight,
  TrendingUp,
  FileText,
  Activity,
  Menu,
  X,
  ChevronRight
} from 'lucide-react';

export default function App() {
  const [user, setUser] = useState(null);

  const handleLogin = (username) => {
    setUser(username || "Marry Jann");
  };

  const handleLogout = () => {
    setUser(null);
  };

  return (
    <div className="min-h-screen w-full bg-[#1e1e1e] font-sans antialiased text-slate-100 selection:bg-yellow-400 selection:text-slate-900">
      {user ? (
        <AdminDashboard username={user} onLogout={handleLogout} />
      ) : (
        <LoginPage onLogin={handleLogin} />
      )}
    </div>
  );
}

function LoginPage({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!username.trim()) {
      setError("Please enter your username");
      return;
    }
    if (!password.trim()) {
      setError("Please enter your password");
      return;
    }

    setError("");
    setIsLoading(true);

    setTimeout(() => {
      setIsLoading(false);
      onLogin(username.trim());
    }, 600);
  };

  return (
    <div className="min-h-screen w-full bg-[#7a7a7a] flex items-center justify-center p-4 sm:p-6 md:p-10 select-none">
      
      {/* =================================================
          FULL-SCREEN RESPONSIVE LOGIN CARD
      ================================================= */}
      <div className="relative w-full max-w-[420px] bg-[#2b2b2b] rounded-3xl shadow-2xl pt-12 pb-10 px-6 sm:px-10 border border-white/5 transition-all duration-300">
        
        {/* FLOATING RACCOON AVATAR AT TOP CENTER */}
        <div className="absolute -top-12 left-1/2 -translate-x-1/2">
          <div className="w-24 h-24 sm:w-28 sm:h-28 rounded-full bg-[#2b2b2b] p-1.5 shadow-xl flex items-center justify-center border border-white/10">
            <div className="w-full h-full rounded-full bg-[#3a3a3a] flex items-center justify-center text-5xl sm:text-6xl border border-white/5">
              🦝
            </div>
          </div>
        </div>

        {/* LOGO TITLE */}
        <div className="text-center mt-2 mb-8">
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-wider text-white">
            RAGcoon
          </h1>
        </div>

        {/* LOGIN FORM */}
        <form onSubmit={handleSubmit} className="space-y-6">
          
          {/* USERNAME FIELD */}
          <div>
            <label className="block text-[11px] font-bold tracking-widest text-slate-300 uppercase text-center mb-2">
              USERNAME
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => {
                setUsername(e.target.value);
                setError("");
              }}
              placeholder=""
              className="w-full h-11 sm:h-12 px-4 rounded-md bg-white text-slate-900 font-medium text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400 transition"
            />
          </div>

          {/* PASSWORD FIELD */}
          <div>
            <label className="block text-[11px] font-bold tracking-widest text-slate-300 uppercase text-center mb-2">
              PASSWORD
            </label>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  setError("");
                }}
                placeholder=""
                className="w-full h-11 sm:h-12 pl-4 pr-12 rounded-md bg-white text-slate-900 font-medium text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400 transition"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-800 p-1"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {/* ERROR ALERT */}
          {error && (
            <div className="p-3 rounded-md bg-red-500/20 border border-red-500/40 text-red-300 text-xs text-center font-medium">
              {error}
            </div>
          )}

          {/* SIGN IN BUTTON */}
          <div className="pt-2">
            <button
              type="submit"
              disabled={isLoading}
              className="w-full h-12 rounded-md bg-[#eed23e] hover:bg-[#e0c430] active:scale-[0.99] text-slate-950 font-bold text-sm tracking-wider uppercase transition shadow-md flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <div className="w-5 h-5 border-2 border-slate-950 border-t-transparent rounded-full animate-spin" />
              ) : (
                "SIGN IN"
              )}
            </button>
          </div>

        </form>

        {/* DEMO AUTOFILL ASSIST */}
        <div className="mt-8 pt-4 border-t border-white/10 text-center">
          <button
            type="button"
            onClick={() => {
              setUsername("Marry Jann");
              setPassword("admin123");
            }}
            className="text-xs text-slate-400 hover:text-yellow-400 underline transition"
          >
            Click to fill Demo Credentials
          </button>
        </div>

      </div>
    </div>
  );
}

function AdminDashboard({ username, onLogout }) {
  const [activeTab, setActiveTab] = useState("Dashboard");
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  // Top metric overview data
  const stats = [
    { label: "Total Document", val: "1256", icon: "📄" },
    { label: "Search Today", val: "456", icon: "📊" },
    { label: "Visits", val: "476", icon: "👁️" },
    { label: "Feedback", val: "1256", icon: "💬" },
  ];

  // Top keyword metrics
  const keywords = [
    { name: "AI", value: 120, bars: 12 },
    { name: "Chatbot", value: 95, bars: 9 },
    { name: "IoT", value: 60, bars: 6 },
    { name: "Automation", value: 40, bars: 4 },
    { name: "Robot", value: 30, bars: 3 },
  ];

  // Most viewed document list
  const mostViewedDocs = [
    { name: "Network Monitoring Document", views: 23 },
    { name: "Pet Feeder", views: 20 },
    { name: "PLC_energy_saver_system", views: 18 },
    { name: "Mobile Automatic Watering Machine", views: 17 },
  ];

  return (
    <div className="min-h-screen bg-[#b5b5b5] text-slate-900 flex flex-col md:flex-row">

      {/* =================================================
          LEFT SIDEBAR NAVIGATION (RESPONSIVE)
      ================================================= */}
      
      {/* Mobile Header Bar */}
      <div className="md:hidden bg-[#2d2d2d] text-white p-4 flex items-center justify-between border-b border-slate-700">
        <div className="flex items-center space-x-3">
          <span className="text-2xl">🦝</span>
          <span className="font-bold text-lg tracking-wide">RAGcoon</span>
        </div>
        <button
          onClick={() => setMobileSidebarOpen(!mobileSidebarOpen)}
          className="p-2 rounded-lg bg-slate-800 text-slate-200"
        >
          {mobileSidebarOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </div>

      {/* Sidebar Panel */}
      <aside className={`
        fixed md:static inset-y-0 left-0 z-40
        w-64 bg-[#2d2d2d] text-slate-200 flex flex-col justify-between
        transform transition-transform duration-300 ease-in-out
        ${mobileSidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
        shrink-0 border-r border-slate-700/50 shadow-2xl md:shadow-none
      `}>
        <div>
          {/* Logo Brand Header */}
          <div className="p-6 flex items-center space-x-3 border-b border-slate-700/50">
            <span className="text-3xl">🦝</span>
            <span className="font-extrabold text-xl tracking-wide text-white">RAGcoon</span>
          </div>

          {/* Navigation Links */}
          <nav className="p-4 space-y-2">
            <button
              onClick={() => { setActiveTab("Dashboard"); setMobileSidebarOpen(false); }}
              className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-semibold transition ${
                activeTab === "Dashboard"
                  ? "bg-white text-slate-950 shadow-sm"
                  : "text-slate-300 hover:bg-slate-800"
              }`}
            >
              <Home className="w-4 h-4" />
              <span>Dashboard</span>
            </button>

            <button
              onClick={() => { setActiveTab("Documents"); setMobileSidebarOpen(false); }}
              className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-semibold transition ${
                activeTab === "Documents"
                  ? "bg-white text-slate-950 shadow-sm"
                  : "text-slate-300 hover:bg-slate-800"
              }`}
            >
              <Folder className="w-4 h-4" />
              <span>Documents Management</span>
            </button>

            <button
              onClick={() => { setActiveTab("Feedback"); setMobileSidebarOpen(false); }}
              className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-semibold transition ${
                activeTab === "Feedback"
                  ? "bg-white text-slate-950 shadow-sm"
                  : "text-slate-300 hover:bg-slate-800"
              }`}
            >
              <MessageSquare className="w-4 h-4" />
              <span>Feedback</span>
            </button>
          </nav>
        </div>

        {/* Sidebar Log Out Button */}
        <div className="p-4 border-t border-slate-700/50">
          <button
            onClick={onLogout}
            className="w-full flex items-center justify-between px-4 py-2.5 rounded-lg bg-white text-slate-950 font-bold text-sm hover:bg-slate-200 transition shadow-sm"
          >
            <span>Log Out</span>
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </aside>

      {/* OVERLAY FOR MOBILE SIDEBAR */}
      {mobileSidebarOpen && (
        <div 
          onClick={() => setMobileSidebarOpen(false)}
          className="fixed inset-0 bg-black/50 z-30 md:hidden backdrop-blur-sm"
        />
      )}

      {/* =================================================
          MAIN DASHBOARD BODY CONTENT
      ================================================= */}
      <main className="flex-1 p-4 sm:p-6 md:p-8 overflow-y-auto space-y-6">
        
        {/* TOP HEADER CONTROLS */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900">
            Overview
          </h2>

          <div className="flex items-center space-x-3 w-full sm:w-auto justify-end">
            {/* Search Input */}
            <div className="relative flex-1 sm:w-64">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Search"
                className="w-full pl-9 pr-4 py-2 text-xs rounded-lg bg-white text-slate-800 placeholder-slate-400 shadow-sm focus:outline-none focus:ring-2 focus:ring-slate-700"
              />
            </div>

            {/* Notification Bell */}
            <button className="p-2 rounded-lg bg-white text-slate-700 shadow-sm hover:bg-slate-50">
              <Bell className="w-4 h-4" />
            </button>

            {/* User Profile */}
            <div className="flex items-center space-x-2 bg-white px-3 py-1.5 rounded-lg shadow-sm">
              <div className="w-6 h-6 rounded-full bg-red-700 flex items-center justify-center text-white text-xs font-bold">
                M
              </div>
              <span className="text-xs font-bold text-slate-800">{username}</span>
            </div>
          </div>
        </div>

        {/* SELECT DATES BUTTON */}
        <div className="flex justify-end">
          <button className="flex items-center space-x-2 bg-white px-3 py-1.5 rounded-md text-xs font-semibold text-slate-700 shadow-sm hover:bg-slate-50">
            <Calendar className="w-3.5 h-3.5" />
            <span>Select Dates</span>
          </button>
        </div>

        {/* =================================================
            METRIC STATS CARDS GRID (4 ITEMS)
        ================================================= */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {stats.map((item, idx) => (
            <div key={idx} className="bg-white p-5 rounded-2xl shadow-sm border border-slate-200/60 flex flex-col justify-between">
              <div className="flex justify-between items-start">
                <span className="text-xs font-semibold text-slate-500">{item.label}</span>
                <span className="text-purple-600 bg-purple-50 p-1.5 rounded-lg text-xs">🟪</span>
              </div>
              <div className="mt-3">
                <div className="text-2xl font-black text-slate-900">{item.val}</div>
                <div className="flex items-center space-x-1 mt-2 text-[10px] font-bold text-teal-600">
                  <span>10%</span>
                  <span>▲</span>
                  <span className="text-slate-400 font-normal">150 today</span>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* =================================================
            CHARTS ROW (LINE & BAR CHART)
        ================================================= */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          
          {/* SEARCH ACTIVITY LINE CHART */}
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200/60">
            <h3 className="text-xs font-bold text-slate-800 tracking-wide uppercase mb-6">
              Search Activity
            </h3>
            <div className="h-48 relative flex items-end">
              {/* Y Axis Labels */}
              <div className="absolute left-0 top-0 bottom-6 flex flex-col justify-between text-[10px] text-slate-400">
                <span>200</span>
                <span>150</span>
                <span>100</span>
                <span>0</span>
              </div>

              {/* Custom SVG Line Graphics */}
              <div className="w-full h-full pl-8 pb-6 pt-2">
                <svg className="w-full h-full overflow-visible" viewBox="0 0 300 120" preserveAspectRatio="none">
                  {/* Grid Lines */}
                  <line x1="0" y1="0" x2="300" y2="0" stroke="#f1f5f9" strokeDasharray="3 3" />
                  <line x1="0" y1="40" x2="300" y2="40" stroke="#f1f5f9" strokeDasharray="3 3" />
                  <line x1="0" y1="80" x2="300" y2="80" stroke="#f1f5f9" strokeDasharray="3 3" />
                  <line x1="0" y1="120" x2="300" y2="120" stroke="#f1f5f9" />

                  {/* Dotted Trend Line */}
                  <path
                    d="M 0 70 Q 50 60 100 80 T 200 40 T 300 10"
                    fill="none"
                    stroke="#93c5fd"
                    strokeWidth="2"
                    strokeDasharray="3 3"
                  />

                  {/* Main Activity Curve */}
                  <path
                    d="M 0 80 C 30 50 50 100 80 80 C 110 60 130 30 160 30 C 190 30 200 60 230 50 C 260 40 280 20 300 25"
                    fill="none"
                    stroke="#475569"
                    strokeWidth="2.5"
                  />
                </svg>
              </div>

              {/* X Axis Month Labels */}
              <div className="absolute bottom-0 left-8 right-0 flex justify-between text-[10px] text-slate-400 font-medium">
                <span>Jan</span>
                <span>Feb</span>
                <span>Mar</span>
                <span>Apr</span>
                <span>May</span>
                <span>Jun</span>
                <span>Jul</span>
              </div>
            </div>
          </div>

          {/* DOCUMENTS BY YEARS BAR CHART */}
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200/60">
            <h3 className="text-xs font-bold text-slate-800 tracking-wide uppercase mb-6">
              Documents by years
            </h3>
            <div className="h-48 flex items-end justify-between px-2 sm:px-6 pt-4">
              {[
                { year: "2018", height: "65%" },
                { year: "2019", height: "85%" },
                { year: "2020", height: "40%" },
                { year: "2021", height: "70%" },
                { year: "2023", height: "50%" },
                { year: "2024", height: "65%" },
                { year: "2025", height: "68%" },
              ].map((bar, i) => (
                <div key={i} className="flex flex-col items-center gap-3 h-full justify-end">
                  <div 
                    className="w-5 sm:w-7 bg-slate-300 rounded-t-lg transition-all duration-500 hover:bg-slate-400"
                    style={{ height: bar.height }}
                  />
                  <span className="text-[10px] font-semibold text-slate-600">{bar.year}</span>
                </div>
              ))}
            </div>
          </div>

        </div>

        {/* =================================================
            BOTTOM ROW (TOP KEYWORDS & MOST VIEWED DOCS)
        ================================================= */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          
          {/* TOP KEYWORDS SECTION */}
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200/60">
            <h3 className="text-xs font-bold text-slate-800 tracking-wide uppercase mb-6">
              Top Keywords
            </h3>
            <div className="space-y-4">
              {keywords.map((kw, idx) => (
                <div key={idx} className="flex items-center justify-between text-xs font-semibold">
                  <span className="w-24 text-slate-700">{kw.name}</span>
                  <div className="flex-1 max-w-[200px] flex gap-1">
                    {Array.from({ length: 12 }).map((_, barIdx) => (
                      <div
                        key={barIdx}
                        className={`h-4 flex-1 rounded-sm ${
                          barIdx < kw.bars ? "bg-slate-900" : "bg-transparent"
                        }`}
                      />
                    ))}
                  </div>
                  <span className="w-10 text-right font-bold text-slate-900">{kw.value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* MOST VIEWED DOCUMENTS SECTION */}
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200/60">
            <h3 className="text-xs font-bold text-slate-800 tracking-wide uppercase mb-6">
              Most Viewed Documents
            </h3>
            <div className="space-y-5">
              {mostViewedDocs.map((doc, idx) => (
                <div key={idx} className="flex items-center justify-between text-xs font-semibold pb-2 border-b border-slate-100 last:border-none">
                  <span className="text-slate-800 font-medium truncate pr-4">{doc.name}</span>
                  <span className="font-bold text-slate-900 shrink-0">{doc.views}</span>
                </div>
              ))}
            </div>
          </div>

        </div>

      </main>
    </div>
  );
}