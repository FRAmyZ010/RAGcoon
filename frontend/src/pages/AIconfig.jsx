import React, { useState } from 'react';
import { 
  Bot, 
  Sliders, 
  MessageSquare, 
  FileText, 
  LayoutDashboard, 
  LogOut, 
  ChevronDown, 
  Pencil, 
  Save, 
  Search, 
  Filter, 
  MoreVertical, 
  Menu, 
  X,
  CheckCircle2,
  Cpu,
  Layers,
  Database,
  Upload,
  User
} from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('ai-config');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [showSaveToast, setShowSaveToast] = useState(false);

  // Form State
  const [model, setModel] = useState('llama3.2');
  const [modelDropdownOpen, setModelDropdownOpen] = useState(false);
  const [temperature, setTemperature] = useState('0.7');
  const [systemPrompt, setSystemPrompt] = useState(
    'You are an AI assistant specialized in answering questions about CE senior projects.\n\nUse ONLY the provided context to answer the question. If the answer is not found in the context, say "I don\'t know" clearly.\n\nBe concise, accurate, and structured. Do not make up information or assumptions.\n\nIf relevant, cite or reference the information from the context.'
  );
  
  // Retrieval State
  const [topK, setTopK] = useState('5');
  const [similarityThreshold, setSimilarityThreshold] = useState('0.7');

  // Embedding State
  const [chunkSize, setChunkSize] = useState('300');
  const [chunkOverlap, setChunkOverlap] = useState('50');
  const [chunkingMethod, setChunkingMethod] = useState('paragraph');
  const [chunkingDropdownOpen, setChunkingDropdownOpen] = useState(false);

  // Feedback State
  const [feedbackSearch, setFeedbackSearch] = useState('');
  const [selectedType, setSelectedType] = useState('All');
  const [selectedStatus, setSelectedStatus] = useState('All');

  const [feedbacks, setFeedbacks] = useState([
    { id: 1, feedback: "I'd like to see a preview of the document before opening it.", type: 'Suggestion', file: 'ProjectPetFeeder', status: 'In Progress', date: '23 Mar 2026' },
    { id: 2, feedback: 'Uploading a PDF shows an error.', type: 'Bug', file: 'ProjectPetFeeder', status: 'Open', date: '21 Mar 2026' },
    { id: 3, feedback: 'The system is slow when performing searches.', type: 'Bug', file: 'ProjectPetFeeder', status: 'In Progress', date: '21 Mar 2026' },
    { id: 4, feedback: 'A dark mode option would be great.', type: 'Suggestion', file: 'ProjectWebapplication', status: 'Resolved', date: '19 Feb 2026' },
    { id: 5, feedback: 'The delete button does not work.', type: 'Bug', file: 'ProjectPetFeeder', status: 'In Progress', date: '19 Feb 2026' },
    { id: 6, feedback: 'Is there support for file types other than PDF?', type: 'Other', file: 'ProjectPetFeeder', status: 'Resolved', date: '23 Jan 2026' },
    { id: 7, feedback: 'The system is easy to use', type: 'Other', file: 'Pre-project_MFU-WIFI', status: 'In Progress', date: '23 Jan 2026' },
    { id: 8, feedback: 'It would be nice if search keywords were highlighted in results.', type: 'Suggestion', file: 'ProjectPetFeeder', status: 'Open', date: '12 Jan 2026' },
  ]);

  const handleSave = () => {
    setShowSaveToast(true);
    setTimeout(() => setShowSaveToast(false), 3000);
  };

  const filteredFeedbacks = feedbacks.filter(item => {
    const matchesSearch = item.feedback.toLowerCase().includes(feedbackSearch.toLowerCase()) || item.file.toLowerCase().includes(feedbackSearch.toLowerCase());
    const matchesType = selectedType === 'All' || item.type === selectedType;
    const matchesStatus = selectedStatus === 'All' || item.status === selectedStatus;
    return matchesSearch && matchesType && matchesStatus;
  });

  return (
    <div className="min-h-screen bg-[#cfcfd4] text-slate-800 font-mono p-3 md:p-6 flex flex-col items-center justify-start">
      {/* Container */}
      <div className="w-full max-w-7xl bg-[#cfcfd4] rounded-2xl flex flex-col lg:flex-row gap-6">
        
        {/* Mobile Header Bar */}
        <div className="lg:hidden w-full bg-[#2b2b2e] text-white p-4 rounded-xl flex items-center justify-between shadow-lg">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center">
              <Bot className="w-5 h-5 text-indigo-400" />
            </div>
            <span className="font-bold text-lg tracking-wider">RAGcoon</span>
          </div>
          <button 
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)} 
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200"
          >
            {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>

        {/* Sidebar Navigation */}
        <aside 
          className={`
            ${mobileMenuOpen ? 'block' : 'hidden'} 
            lg:block bg-[#2b2b2e] text-slate-200 rounded-xl p-4 flex flex-col justify-between transition-all duration-300 shadow-xl shrink-0
            ${sidebarCollapsed ? 'lg:w-20' : 'lg:w-64'}
          `}
        >
          <div className="space-y-6">
            {/* Header / Logo */}
            <div className="flex items-center justify-between pb-4 border-b border-slate-700">
              <div className="flex items-center gap-3 overflow-hidden">
                <div className="w-9 h-9 rounded-xl bg-slate-800 flex items-center justify-center shrink-0 border border-slate-600">
                  <Bot className="w-6 h-6 text-indigo-400" />
                </div>
                {!sidebarCollapsed && (
                  <span className="font-bold text-xl tracking-wider text-white">RAGcoon</span>
                )}
              </div>
              <button 
                onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
                className="hidden lg:flex p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white"
              >
                <Sliders className="w-5 h-5" />
              </button>
            </div>

            {/* Nav Menu */}
            <nav className="space-y-2">
              <button
                onClick={() => { setActiveTab('dashboard'); setMobileMenuOpen(false); }}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  activeTab === 'dashboard' ? 'bg-slate-100 text-slate-900 shadow' : 'hover:bg-slate-800 text-slate-300'
                }`}
              >
                <LayoutDashboard className="w-5 h-5 shrink-0" />
                {!sidebarCollapsed && <span>Dashboard</span>}
              </button>

              <button
                onClick={() => { setActiveTab('ai-config'); setMobileMenuOpen(false); }}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  activeTab === 'ai-config' ? 'bg-slate-100 text-slate-900 shadow' : 'hover:bg-slate-800 text-slate-300'
                }`}
              >
                <Sliders className="w-5 h-5 shrink-0" />
                {!sidebarCollapsed && <span>AI Configuration</span>}
              </button>

              <button
                onClick={() => { setActiveTab('documents'); setMobileMenuOpen(false); }}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  activeTab === 'documents' ? 'bg-slate-100 text-slate-900 shadow' : 'hover:bg-slate-800 text-slate-300'
                }`}
              >
                <FileText className="w-5 h-5 shrink-0" />
                {!sidebarCollapsed && <span>Documents Management</span>}
              </button>

              <button
                onClick={() => { setActiveTab('feedback'); setMobileMenuOpen(false); }}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  activeTab === 'feedback' ? 'bg-slate-100 text-slate-900 shadow' : 'hover:bg-slate-800 text-slate-300'
                }`}
              >
                <MessageSquare className="w-5 h-5 shrink-0" />
                {!sidebarCollapsed && <span>Feedback</span>}
              </button>
            </nav>
          </div>

          {/* Sidebar Footer */}
          <div className="pt-6 border-t border-slate-700">
            <button className="w-full flex items-center justify-between px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors">
              {!sidebarCollapsed && <span className="text-xs">Log out</span>}
              <LogOut className="w-4 h-4 text-slate-400" />
            </button>
          </div>
        </aside>

        {/* Main Content View Container */}
        <main className="flex-1 flex flex-col gap-6 w-full">
          
          {/* User Header */}
          <div className="flex items-center justify-between px-2">
            <h1 className="text-2xl font-extrabold text-slate-900">
              {activeTab === 'ai-config' && 'AI Configuration'}
              {activeTab === 'feedback' && 'Feedback'}
              {activeTab === 'dashboard' && 'Dashboard'}
              {activeTab === 'documents' && 'Documents Management'}
            </h1>
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-purple-600 flex items-center justify-center text-white">
                <User className="w-4 h-4" />
              </div>
              <span className="text-sm font-bold text-slate-800 hidden sm:inline">Gyro Zeppelli</span>
            </div>
          </div>

          {/* Tab 1: AI CONFIGURATION */}
          {activeTab === 'ai-config' && (
            <div className="space-y-6">
              {/* Two-Column Grid Layout */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
                
                {/* LEFT COLUMN: LLM PARAMETER */}
                <div className="bg-[#2b2b2e] text-white p-5 md:p-6 rounded-2xl shadow-xl space-y-6">
                  <div className="flex items-center gap-3 border-b border-slate-700 pb-3">
                    <Layers className="w-6 h-6 text-indigo-400" />
                    <h2 className="text-xl font-bold tracking-wide">LLM PARAMETER</h2>
                  </div>

                  {/* Model LLM Selection */}
                  <div className="space-y-2 relative">
                    <label className="text-xs text-slate-300 font-semibold uppercase">Model LLM Selection</label>
                    <button
                      onClick={() => setModelDropdownOpen(!modelDropdownOpen)}
                      className="w-full bg-white text-slate-900 px-4 py-3 rounded-xl flex items-center justify-between font-bold text-sm shadow-sm hover:bg-slate-50 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-6 h-6 bg-slate-100 rounded flex items-center justify-center border border-slate-300">
                          <Bot className="w-4 h-4 text-slate-700" />
                        </div>
                        <span>{model}</span>
                      </div>
                      <ChevronDown className="w-5 h-5 text-slate-600" />
                    </button>

                    {/* Custom Dropdown Options */}
                    {modelDropdownOpen && (
                      <div className="absolute left-0 right-0 top-full mt-2 bg-white rounded-xl shadow-2xl border border-slate-200 z-20 py-2 text-slate-800 space-y-1">
                        {['llama3.2', 'llama3.1', 'llama4'].map((m) => (
                          <button
                            key={m}
                            onClick={() => { setModel(m); setModelDropdownOpen(false); }}
                            className={`w-full px-4 py-2.5 text-left text-sm font-semibold flex items-center gap-3 hover:bg-slate-100 transition-colors ${model === m ? 'bg-slate-100 text-indigo-600' : ''}`}
                          >
                            <Bot className="w-4 h-4 text-slate-500" />
                            {m}
                          </button>
                        ))}
                      </div>
                    )}
                    <p className="text-[10px] text-slate-400 italic">** System default</p>
                  </div>

                  {/* LLM Temperature */}
                  <div className="space-y-2">
                    <label className="text-xs text-slate-300 font-semibold uppercase">LLM Temperature</label>
                    <div className="relative">
                      <input
                        type="text"
                        value={temperature}
                        onChange={(e) => setTemperature(e.target.value)}
                        className="w-full bg-white text-slate-900 font-bold px-4 py-3 rounded-xl pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      />
                      <Pencil className="w-4 h-4 text-slate-400 absolute right-3 top-3.5 pointer-events-none" />
                    </div>
                    <p className="text-[10px] text-slate-400 italic">** System default</p>
                  </div>

                  {/* System Prompt */}
                  <div className="space-y-2">
                    <label className="text-xs text-slate-300 font-semibold uppercase">System Prompt</label>
                    <div className="relative bg-white rounded-xl p-3 shadow-inner">
                      <Pencil className="w-4 h-4 text-slate-400 absolute top-3 left-3" />
                      <textarea
                        rows={7}
                        value={systemPrompt}
                        onChange={(e) => setSystemPrompt(e.target.value)}
                        className="w-full pl-7 pr-2 py-1 text-xs text-slate-800 font-mono leading-relaxed bg-transparent focus:outline-none resize-none"
                      />
                    </div>
                    <p className="text-[10px] text-slate-400 italic">** System default</p>
                  </div>
                </div>

                {/* RIGHT COLUMN: RETRIEVAL & EMBEDDING PARAMETERS */}
                <div className="space-y-6">
                  
                  {/* Retrieval Parameter Card */}
                  <div className="bg-[#2b2b2e] text-white p-5 md:p-6 rounded-2xl shadow-xl space-y-6">
                    <div className="flex items-center gap-3 border-b border-slate-700 pb-3">
                      <Search className="w-6 h-6 text-indigo-400" />
                      <h2 className="text-xl font-bold tracking-wide">Retrieval Parameter</h2>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      {/* top_k */}
                      <div className="space-y-2">
                        <label className="text-xs text-slate-300 font-semibold uppercase">top_k</label>
                        <div className="relative">
                          <input
                            type="text"
                            value={topK}
                            onChange={(e) => setTopK(e.target.value)}
                            className="w-full bg-white text-slate-900 font-bold px-4 py-3 rounded-xl pr-10 text-sm focus:outline-none"
                          />
                          <Pencil className="w-4 h-4 text-slate-400 absolute right-3 top-3.5" />
                        </div>
                        <p className="text-[10px] text-slate-400 italic">** System default</p>
                      </div>

                      {/* similarity_threshold */}
                      <div className="space-y-2">
                        <label className="text-xs text-slate-300 font-semibold uppercase">similarity_threshold</label>
                        <div className="relative">
                          <input
                            type="text"
                            value={similarityThreshold}
                            onChange={(e) => setSimilarityThreshold(e.target.value)}
                            className="w-full bg-white text-slate-900 font-bold px-4 py-3 rounded-xl pr-10 text-sm focus:outline-none"
                          />
                          <Pencil className="w-4 h-4 text-slate-400 absolute right-3 top-3.5" />
                        </div>
                        <p className="text-[10px] text-slate-400 italic">** System default</p>
                      </div>
                    </div>
                  </div>

                  {/* Embedding Parameter Card */}
                  <div className="bg-[#2b2b2e] text-white p-5 md:p-6 rounded-2xl shadow-xl space-y-6">
                    <div className="flex items-center gap-3 border-b border-slate-700 pb-3">
                      <Database className="w-6 h-6 text-indigo-400" />
                      <h2 className="text-xl font-bold tracking-wide">Embedding Parameter</h2>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      {/* chunk_size */}
                      <div className="space-y-2">
                        <label className="text-xs text-slate-300 font-semibold uppercase">chunk_size</label>
                        <div className="relative">
                          <input
                            type="text"
                            value={chunkSize}
                            onChange={(e) => setChunkSize(e.target.value)}
                            className="w-full bg-white text-slate-900 font-bold px-4 py-3 rounded-xl pr-10 text-sm focus:outline-none"
                          />
                          <Pencil className="w-4 h-4 text-slate-400 absolute right-3 top-3.5" />
                        </div>
                        <p className="text-[10px] text-slate-400 italic">** System default</p>
                      </div>

                      {/* chunk_overlap */}
                      <div className="space-y-2">
                        <label className="text-xs text-slate-300 font-semibold uppercase">chunk_overlap</label>
                        <div className="relative">
                          <input
                            type="text"
                            value={chunkOverlap}
                            onChange={(e) => setChunkOverlap(e.target.value)}
                            className="w-full bg-white text-slate-900 font-bold px-4 py-3 rounded-xl pr-10 text-sm focus:outline-none"
                          />
                          <Pencil className="w-4 h-4 text-slate-400 absolute right-3 top-3.5" />
                        </div>
                        <p className="text-[10px] text-slate-400 italic">** System default</p>
                      </div>
                    </div>

                    {/* Chunking method */}
                    <div className="space-y-2 relative">
                      <label className="text-xs text-slate-300 font-semibold uppercase">Chunking method</label>
                      <button
                        onClick={() => setChunkingDropdownOpen(!chunkingDropdownOpen)}
                        className="w-full bg-white text-slate-900 px-4 py-3 rounded-xl flex items-center justify-between font-bold text-sm shadow-sm hover:bg-slate-50 transition-colors"
                      >
                        <span>{chunkingMethod}</span>
                        <ChevronDown className="w-5 h-5 text-slate-600" />
                      </button>

                      {chunkingDropdownOpen && (
                        <div className="absolute left-0 right-0 top-full mt-2 bg-white rounded-xl shadow-2xl border border-slate-200 z-20 py-2 text-slate-800 space-y-1">
                          {['paragraph', 'sentence', 'fixed size'].map((method) => (
                            <button
                              key={method}
                              onClick={() => { setChunkingMethod(method); setChunkingDropdownOpen(false); }}
                              className={`w-full px-4 py-2.5 text-left text-sm font-semibold hover:bg-slate-100 transition-colors ${chunkingMethod === method ? 'bg-slate-100 text-indigo-600' : ''}`}
                            >
                              {method}
                            </button>
                          ))}
                        </div>
                      )}
                      <p className="text-[10px] text-slate-400 italic">** System default</p>
                    </div>
                  </div>

                </div>
              </div>

              {/* Action Save Button */}
              <div className="flex items-center justify-start pt-2">
                <button
                  onClick={handleSave}
                  className="bg-blue-600 hover:bg-blue-500 active:bg-blue-700 text-white font-bold px-6 py-3 rounded-xl flex items-center gap-3 shadow-lg hover:shadow-xl transition-all"
                >
                  <Save className="w-5 h-5" />
                  <span>Save configuration</span>
                </button>
              </div>
            </div>
          )}

          {/* Tab 2: FEEDBACK VIEW */}
          {activeTab === 'feedback' && (
            <div className="bg-white rounded-2xl shadow-xl p-4 md:p-6 space-y-6">
              
              {/* Filters Header */}
              <div className="flex flex-col md:flex-row gap-4 items-start md:items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold text-slate-900">{feedbacks.length} Feedbacks</h2>
                </div>

                <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
                  {/* Search input */}
                  <div className="relative flex-1 sm:w-64">
                    <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
                    <input
                      type="text"
                      placeholder="Search..."
                      value={feedbackSearch}
                      onChange={(e) => setFeedbackSearch(e.target.value)}
                      className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>

                  {/* Filter Type */}
                  <select
                    value={selectedType}
                    onChange={(e) => setSelectedType(e.target.value)}
                    className="px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-mono text-slate-700 focus:outline-none"
                  >
                    <option value="All">Type: All</option>
                    <option value="Suggestion">Suggestion</option>
                    <option value="Bug">Bug</option>
                    <option value="Other">Other</option>
                  </select>

                  {/* Filter Status */}
                  <select
                    value={selectedStatus}
                    onChange={(e) => setSelectedStatus(e.target.value)}
                    className="px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-mono text-slate-700 focus:outline-none"
                  >
                    <option value="All">Status: All</option>
                    <option value="Open">Open</option>
                    <option value="In Progress">In Progress</option>
                    <option value="Resolved">Resolved</option>
                  </select>
                </div>
              </div>

              {/* Data Table */}
              <div className="w-full">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-slate-100 text-slate-700 text-xs uppercase font-bold border-b border-slate-200">
                      <th className="py-3.5 px-4 rounded-l-xl">Feedback</th>
                      <th className="py-3.5 px-4">Type</th>
                      <th className="py-3.5 px-4">File</th>
                      <th className="py-3.5 px-4">Status</th>
                      <th className="py-3.5 px-4">Date</th>
                      <th className="py-3.5 px-4 rounded-r-xl text-right"></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-xs">
                    {filteredFeedbacks.map((row) => (
                      <tr key={row.id} className="hover:bg-slate-50/80 transition-colors">
                        <td className="py-4 px-4 font-sans font-medium text-slate-800 max-w-xs md:max-w-md">
                          {row.feedback}
                        </td>
                        <td className="py-4 px-4 font-mono text-slate-600">
                          {row.type}
                        </td>
                        <td className="py-4 px-4 font-mono font-semibold text-slate-700">
                          {row.file}
                        </td>
                        <td className="py-4 px-4">
                          <span className={`inline-block px-2.5 py-1 rounded-full text-[11px] font-bold ${
                            row.status === 'In Progress' ? 'bg-amber-100 text-amber-800' :
                            row.status === 'Open' ? 'bg-rose-100 text-rose-800' :
                            'bg-emerald-100 text-emerald-800'
                          }`}>
                            {row.status}
                          </span>
                        </td>
                        <td className="py-4 px-4 font-mono text-slate-500 whitespace-nowrap">
                          {row.date}
                        </td>
                        <td className="py-4 px-4 text-right">
                          <button className="p-1 hover:bg-slate-200 rounded text-slate-500">
                            <MoreVertical className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Tab 3: DASHBOARD */}
          {activeTab === 'dashboard' && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
              <div className="bg-white p-6 rounded-2xl shadow-lg space-y-2">
                <span className="text-xs text-slate-500 uppercase font-bold">Total Embeddings</span>
                <p className="text-3xl font-extrabold text-slate-900">12,482</p>
                <p className="text-xs text-emerald-600 font-bold">+12% from last week</p>
              </div>
              <div className="bg-white p-6 rounded-2xl shadow-lg space-y-2">
                <span className="text-xs text-slate-500 uppercase font-bold">Average Latency</span>
                <p className="text-3xl font-extrabold text-slate-900">142 ms</p>
                <p className="text-xs text-emerald-600 font-bold">-8% faster</p>
              </div>
              <div className="bg-white p-6 rounded-2xl shadow-lg space-y-2">
                <span className="text-xs text-slate-500 uppercase font-bold">Active LLM Model</span>
                <p className="text-3xl font-extrabold text-indigo-600">{model}</p>
                <p className="text-xs text-slate-400 font-bold">Ready & Operational</p>
              </div>
            </div>
          )}

          {/* Tab 4: DOCUMENTS MANAGEMENT */}
          {activeTab === 'documents' && (
            <div className="bg-white rounded-2xl shadow-xl p-6 space-y-6">
              <div className="flex items-center justify-between border-b pb-4">
                <h2 className="text-lg font-bold text-slate-900">Knowledge Base Files</h2>
                <button className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold px-4 py-2 rounded-xl text-xs flex items-center gap-2">
                  <Upload className="w-4 h-4" /> Upload Document
                </button>
              </div>
              <div className="space-y-3">
                {['ProjectPetFeeder.pdf', 'ProjectWebapplication.pdf', 'Pre-project_MFU-WIFI.pdf'].map((doc, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 bg-slate-50 rounded-xl border border-slate-200">
                    <div className="flex items-center gap-3">
                      <FileText className="w-5 h-5 text-indigo-600" />
                      <span className="text-xs font-bold text-slate-800">{doc}</span>
                    </div>
                    <span className="text-[10px] bg-slate-200 text-slate-700 font-bold px-2.5 py-1 rounded-md">Indexed</span>
                  </div>
                ))}
              </div>
            </div>
          )}

        </main>
      </div>

      {/* Save Toast Alert */}
      {showSaveToast && (
        <div className="fixed bottom-6 right-6 bg-slate-900 text-white px-5 py-3 rounded-xl shadow-2xl flex items-center gap-3 z-50 border border-slate-700 animate-bounce">
          <CheckCircle2 className="w-5 h-5 text-emerald-400" />
          <span className="text-xs font-bold">AI Configuration saved successfully!</span>
        </div>
      )}
    </div>
  );
}