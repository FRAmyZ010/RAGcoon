import React, { useState } from 'react';
import { 
  ResponsiveContainer, 
  AreaChart, 
  Area, 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  Tooltip 
} from 'recharts';
import { 
  LayoutDashboard, 
  FolderKanban, 
  MessageSquareQuote, 
  LogOut, 
  Search, 
  Bell, 
  Calendar, 
  ChevronLeft, 
  ChevronRight, 
  TrendingUp, 
  Menu, 
  X,
  PieChart
} from 'lucide-react';

const searchActivityData = [
  { month: 'Jan', current: 100, previous: 120 },
  { month: 'Feb', current: 130, previous: 110 },
  { month: 'Mar', current: 120, previous: 160 },
  { month: 'Apr', current: 175, previous: 110 },
  { month: 'May', current: 160, previous: 130 },
  { month: 'Jun', current: 140, previous: 180 },
  { month: 'Jul', current: 170, previous: 195 },
];

const documentsByYearData = [
  { year: '2018', count: 180 },
  { year: '2019', count: 220 },
  { year: '2020', count: 110 },
  { year: '2021', count: 185 },
  { year: '2023', count: 150 },
  { year: '2024', count: 180 },
  { year: '2025', count: 185 },
];

const topKeywords = [
  { name: 'AI', count: 120, max: 120 },
  { name: 'Chatbot', count: 95, max: 120 },
  { name: 'IoT', count: 60, max: 120 },
  { name: 'Automation', count: 40, max: 120 },
  { name: 'Robot', count: 30, max: 120 },
];

const mostViewedDocs = [
  { id: 1, title: 'Network Monitoring Document', views: 23 },
  { id: 2, title: 'Pet Feeder', views: 20 },
  { id: 3, title: 'PLC_energy_saver_system', views: 18 },
  { id: 4, title: 'Mobile Automatic Watering Machine', views: 17 },
];

export default function App() {
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [searchQuery, setSearchQuery] = useState('');

  const RAGcoonLogo = ({ size = "normal" }) => (
    <div className="flex items-center gap-2.5">
      <div className="w-8 h-8 rounded-xl bg-neutral-800 border border-neutral-700 flex items-center justify-center shrink-0 shadow-inner overflow-hidden relative">
        <div className="w-full h-full bg-neutral-900 flex items-center justify-center relative">
          <div className="absolute w-6 h-3 bg-neutral-700 rounded-full top-1.5"></div>
          <div className="absolute w-1.5 h-1.5 bg-white rounded-full top-2.5 left-1 border border-black flex items-center justify-center">
            <div className="w-0.5 h-0.5 bg-black rounded-full"></div>
          </div>
          <div className="absolute w-1.5 h-1.5 bg-white rounded-full top-2.5 right-1 border border-black flex items-center justify-center">
            <div className="w-0.5 h-0.5 bg-black rounded-full"></div>
          </div>
          <div className="absolute w-1.5 h-1 bg-neutral-300 rounded-b-md bottom-1"></div>
        </div>
      </div>
      {size !== "small" && (
        <span className="font-mono font-bold text-lg tracking-tight text-white select-none">
          RAGcoon
        </span>
      )}
    </div>
  );

  return (
    <div className="h-screen w-screen bg-[#b2b5b8] text-slate-800 font-sans antialiased flex flex-col md:flex-row p-0 md:p-3 gap-0 md:gap-3 overflow-hidden select-none">
      
      {/* Mobile Top Nav */}
      <div className="md:hidden bg-[#2d2e30] text-white p-3 flex justify-between items-center shrink-0 z-40 shadow-md">
        <RAGcoonLogo />
        <button 
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          className="p-1.5 text-gray-300 hover:text-white rounded-lg focus:outline-none"
        >
          {isMobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      <aside 
        className={`
          fixed md:relative inset-y-0 left-0 z-50 h-full
          bg-[#2b2b2b] text-white flex flex-col justify-between p-3.5 rounded-none md:rounded-2xl transition-all duration-300 ease-in-out shadow-xl shrink-0 overflow-hidden
          ${isSidebarCollapsed ? 'md:w-16' : 'md:w-56'}
          ${isMobileMenuOpen ? 'translate-x-0 w-56' : '-translate-x-full md:translate-x-0'}
        `}
      >
        <div className="flex flex-col gap-5">
          {/* Sidebar Header */}
          <div className="flex items-center justify-between px-0.5 pt-0.5">
            <RAGcoonLogo size={isSidebarCollapsed ? "small" : "normal"} />
            <button 
              onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
              className="hidden md:flex text-gray-400 hover:text-white p-1 rounded-md transition-colors hover:bg-neutral-800"
              title={isSidebarCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
            >
              {isSidebarCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
            </button>
          </div>

          {/* Nav Links */}
          <nav className="space-y-1.5">
            <button
              onClick={() => { setActiveTab('dashboard'); setIsMobileMenuOpen(false); }}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium transition-all ${
                activeTab === 'dashboard' 
                  ? 'bg-white text-black font-semibold shadow-sm' 
                  : 'text-gray-300 hover:bg-neutral-800 hover:text-white'
              }`}
            >
              <LayoutDashboard size={16} className={activeTab === 'dashboard' ? 'text-black' : 'text-gray-300'} />
              {(!isSidebarCollapsed || isMobileMenuOpen) && <span className="truncate">Dashboard</span>}
            </button>

            <button
              onClick={() => { setActiveTab('documents'); setIsMobileMenuOpen(false); }}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium transition-all ${
                activeTab === 'documents' 
                  ? 'bg-white text-black font-semibold shadow-sm' 
                  : 'text-gray-300 hover:bg-neutral-800 hover:text-white'
              }`}
            >
              <FolderKanban size={16} className={activeTab === 'documents' ? 'text-black' : 'text-gray-300'} />
              {(!isSidebarCollapsed || isMobileMenuOpen) && <span className="truncate">Documents Management</span>}
            </button>

            <button
              onClick={() => { setActiveTab('feedback'); setIsMobileMenuOpen(false); }}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium transition-all ${
                activeTab === 'feedback' 
                  ? 'bg-white text-black font-semibold shadow-sm' 
                  : 'text-gray-300 hover:bg-neutral-800 hover:text-white'
              }`}
            >
              <MessageSquareQuote size={16} className={activeTab === 'feedback' ? 'text-black' : 'text-gray-300'} />
              {(!isSidebarCollapsed || isMobileMenuOpen) && <span className="truncate">Feedback</span>}
            </button>
          </nav>
        </div>

        {/* Sidebar Footer */}
        <div className="pt-2 border-t border-neutral-700/50">
          <button 
            onClick={() => alert("Logged out successfully")}
            className={`w-full flex items-center ${isSidebarCollapsed && !isMobileMenuOpen ? 'justify-center px-0' : 'justify-between px-3'} py-2 bg-neutral-100 text-black font-mono font-medium rounded-xl hover:bg-neutral-200 transition-colors shadow-sm`}
          >
            {(!isSidebarCollapsed || isMobileMenuOpen) && <span className="text-xs">Log Out</span>}
            <LogOut size={15} />
          </button>
        </div>
      </aside>

      <main className="flex-1 bg-[#bec1c4] p-3 md:p-4 rounded-none md:rounded-2xl flex flex-col justify-between gap-3 h-full overflow-hidden">
        
        {/* Header Bar */}
        <header className="flex flex-col sm:flex-row items-center justify-between gap-2 shrink-0">
          <h1 className="text-xl font-mono font-bold tracking-tight text-neutral-900">Overview</h1>

          <div className="flex items-center gap-2.5 w-full sm:w-auto justify-end">
            {/* Search Input */}
            <div className="relative flex-1 sm:w-48">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" size={14} />
              <input 
                type="text" 
                placeholder="Search" 
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-white text-gray-800 pl-8 pr-3 py-1 rounded-lg text-xs font-mono border-none focus:ring-2 focus:ring-neutral-400 focus:outline-none shadow-sm"
              />
            </div>

            {/* Notification */}
            <button className="p-1.5 bg-transparent text-neutral-800 hover:text-black rounded-full transition-colors relative">
              <Bell size={16} />
              <span className="absolute top-1 right-1 w-1.5 h-1.5 bg-red-500 rounded-full"></span>
            </button>

            {/* Profile */}
            <div className="flex items-center gap-1.5 px-1">
              <div className="w-6 h-6 rounded-full bg-red-600 flex items-center justify-center text-white font-bold text-[10px] shadow-sm">
                M
              </div>
              <span className="text-[11px] font-mono font-medium text-neutral-800 whitespace-nowrap hidden lg:inline">Marry Jann</span>
            </div>

            {/* Select Dates */}
            <button className="flex items-center gap-1.5 bg-white px-2.5 py-1 rounded-lg text-[11px] font-mono text-neutral-700 hover:bg-neutral-50 shadow-sm border border-neutral-200/80 transition-all">
              <Calendar size={13} className="text-neutral-500" />
              <span className="whitespace-nowrap">Select Dates</span>
            </button>
          </div>
        </header>

        {/* Top 4 Summary Cards Grid */}
        <section className="grid grid-cols-2 lg:grid-cols-4 gap-2.5 shrink-0">
          {[
            { title: 'Total Document', count: '1256' },
            { title: 'Search Today', count: '456' },
            { title: 'Visits', count: '476' },
            { title: 'Feedback', count: '1256' },
          ].map((card, idx) => (
            <div key={idx} className="bg-white p-2.5 rounded-xl shadow-sm border border-neutral-100 flex flex-col justify-between">
              <div className="flex justify-between items-center mb-1">
                <span className="text-[11px] font-mono font-medium text-neutral-500 truncate">{card.title}</span>
                <div className="p-1 rounded-md bg-purple-100 text-purple-600 shrink-0">
                  <PieChart size={13} />
                </div>
              </div>
              <div>
                <div className="text-xl font-mono font-bold text-neutral-900 leading-tight mb-0.5">{card.count}</div>
                <div className="flex items-center gap-1 text-[10px] font-mono text-emerald-600 font-medium">
                  <span>10%</span>
                  <TrendingUp size={10} />
                  <span className="text-neutral-400 ml-0.5">150 today</span>
                </div>
              </div>
            </div>
          ))}
        </section>

        <section className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-2.5 min-h-0">
          
          {/* Search Activity Chart */}
          <div className="bg-white p-3 rounded-xl shadow-sm border border-neutral-100 flex flex-col justify-between overflow-hidden">
            <h3 className="text-[11px] font-mono font-bold text-neutral-800 tracking-wide mb-1 shrink-0">Search Activity</h3>
            <div className="flex-1 w-full min-h-0">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={searchActivityData} margin={{ top: 5, right: 10, left: -28, bottom: -5 }}>
                  <defs>
                    <linearGradient id="colorCurrent" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#4b5563" stopOpacity={0.15}/>
                      <stop offset="95%" stopColor="#4b5563" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fontSize: 9, fill: '#9ca3af', fontFamily: 'monospace' }} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 9, fill: '#9ca3af', fontFamily: 'monospace' }} domain={[0, 200]} ticks={[0, 100, 150, 200]} />
                  <Tooltip contentStyle={{ backgroundColor: '#1f2937', color: '#fff', borderRadius: '6px', fontSize: '10px', padding: '4px 8px' }} />
                  <Area type="monotone" dataKey="current" stroke="#374151" strokeWidth={1.5} fillOpacity={1} fill="url(#colorCurrent)" />
                  <Area type="monotone" dataKey="previous" stroke="#93c5fd" strokeWidth={1.5} strokeDasharray="2 2" fill="none" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Documents by Years Chart */}
          <div className="bg-white p-3 rounded-xl shadow-sm border border-neutral-100 flex flex-col justify-between overflow-hidden">
            <h3 className="text-[11px] font-mono font-bold text-neutral-800 tracking-wide mb-1 shrink-0">Documents by years</h3>
            <div className="flex-1 w-full min-h-0">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={documentsByYearData} margin={{ top: 5, right: 10, left: -20, bottom: -5 }}>
                  <XAxis dataKey="year" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#374151', fontFamily: 'monospace', fontWeight: 'bold' }} />
                  <YAxis hide={true} domain={[0, 250]} />
                  <Tooltip cursor={{ fill: 'transparent' }} contentStyle={{ backgroundColor: '#1f2937', color: '#fff', borderRadius: '6px', fontSize: '10px', padding: '4px 8px' }} />
                  <Bar dataKey="count" fill="#c4c4c4" radius={[6, 6, 6, 6]} barSize={22} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Top Keywords Progress Bars */}
          <div className="bg-white p-3 rounded-xl shadow-sm border border-neutral-100 flex flex-col justify-between overflow-hidden">
            <h3 className="text-[11px] font-mono font-bold text-neutral-800 tracking-wide mb-1 shrink-0">Top Keywords</h3>
            <div className="flex-1 flex flex-col justify-around py-0.5">
              {topKeywords.map((item, idx) => {
                const percentage = (item.count / item.max) * 100;
                return (
                  <div key={idx} className="flex items-center justify-between gap-3 font-mono text-[11px]">
                    <span className="w-20 font-bold text-neutral-800 truncate">{item.name}</span>
                    <div className="flex-1 bg-neutral-100 h-4 rounded-sm overflow-hidden flex items-center p-0.5">
                      <div 
                        className="bg-black h-full rounded-sm transition-all duration-500 ease-out" 
                        style={{ width: `${percentage}%` }}
                      ></div>
                    </div>
                    <span className="w-6 text-right font-bold text-neutral-800">{item.count}</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Most Viewed Documents */}
          <div className="bg-white p-3 rounded-xl shadow-sm border border-neutral-100 flex flex-col justify-between overflow-hidden">
            <h3 className="text-[11px] font-mono font-bold text-neutral-800 tracking-wide mb-1 shrink-0">Most Viewed Documents</h3>
            <div className="flex-1 flex flex-col justify-around py-0.5">
              {mostViewedDocs.map((doc) => (
                <div key={doc.id} className="flex items-center justify-between text-[11px] font-mono hover:bg-neutral-50 px-1 py-0.5 rounded transition-colors">
                  <span className="font-bold text-neutral-800 truncate max-w-[85%]">
                    {doc.title}
                  </span>
                  <span className="font-bold text-neutral-800">{doc.views}</span>
                </div>
              ))}
            </div>
          </div>

        </section>

      </main>

    </div>
  );
}