import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  Check,
  ChevronRight,
  Copy,
  ExternalLink,
  FileText,
  FolderClosed,
  Menu,
  MessageSquarePlus,
  PanelLeftClose,
  RefreshCw,
  Search,
  SendHorizontal,
  ThumbsDown,
  ThumbsUp,
  X,
  ChevronRight,
  Star,
  Upload,
  Pencil
} from 'lucide-react';

export default function App() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [workspaces, setWorkspaces] = useState([]);
  const [activeWorkspaceId, setActiveWorkspaceId] = useState(null);
  const [activeWorkspaceTitle, setActiveWorkspaceTitle] = useState("New chat");
  const [showCitationsIndex, setShowCitationsIndex] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [feedback, setFeedback] = useState({});
  const [copiedIndex, setCopiedIndex] = useState(null);

  const chatEndRef = useRef(null);
  const inputRef = useRef(null);

  const resizeComposer = () => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = "auto";
    const maxPx = 160; // ~ max-h-40
    el.style.height = `${Math.min(el.scrollHeight, maxPx)}px`;
  };

  useEffect(() => {
    fetchWorkspaces();
    if (window.innerWidth >= 1024) {
      setSidebarOpen(true);
    }
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    resizeComposer();
  }, [input]);

  const fetchWorkspaces = async () => {
    try {
      const res = await fetch("/api/v1/chat/workspaces");
      if (res.ok) {
        setWorkspaces(await res.json());
      }
    } catch (err) {
      console.error("Failed to load workspaces:", err);
    }
  };

  const handleNewWorkspace = () => {
    const newWorkspaceId = `ws-${crypto.randomUUID().slice(0, 12)}`;
    setActiveWorkspaceId(newWorkspaceId);
    setActiveWorkspaceTitle("New chat");
    setMessages([]);
    setShowCitationsIndex(null);
    setFeedback({});
    inputRef.current?.focus();
  };

  const handleSelectWorkspace = async (ws) => {
    setActiveWorkspaceId(ws.workspace_id);
    setActiveWorkspaceTitle(ws.title);
    setLoading(true);
    setShowCitationsIndex(null);

    if (window.innerWidth < 1024) {
      setSidebarOpen(false);
    }

    try {
      const res = await fetch(`/api/v1/chat/workspaces/${ws.workspace_id}`);
      if (res.ok) {
        const data = await res.json();
        const formattedMessages = [];

        data.queries.forEach((q) => {
          formattedMessages.push({ role: "user", text: q.query_text });
          formattedMessages.push({
            role: "bot",
            text: q.response_text,
            citations: q.retrieved_docs?.citations || [],
            meta: q.retrieved_docs?.timing
              ? `Total ${formatSeconds(q.retrieved_docs.timing.total_seconds)}s`
              : "",
          });
        });

        setMessages(formattedMessages);
      }
    } catch (err) {
      console.error("Failed to load workspace detail:", err);
    } finally {
      setLoading(false);
    }
  };

  const streamQuery = async (userQuery, workspaceId = activeWorkspaceId, options = {}) => {
    const { replaceBotIndex = null } = options;
    setLoading(true);

    let botMsgIndex;
    if (replaceBotIndex != null) {
      botMsgIndex = replaceBotIndex;
      setMessages((prev) => {
        const updated = [...prev];
        updated[botMsgIndex] = {
          role: "bot",
          text: "",
          citations: [],
          meta: "Searching...",
          model: null,
        };
        return updated;
      });
    } else {
      botMsgIndex = messages.length + 1;
      setMessages((prev) => [
        ...prev,
        { role: "user", text: userQuery },
        { role: "bot", text: "", citations: [], meta: "Searching..." },
      ]);
    }

    try {
      const response = await fetch("/api/v1/chat/query-stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query_text: userQuery,
          workspace_id: workspaceId,
        }),
      });

      if (!response.body) throw new Error("ReadableStream not supported");

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let currentText = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n\n");

        for (const line of lines) {
          if (!line.trim()) continue;

          const dataLine = line.split("\n").find((l) => l.startsWith("data: "));
          if (!dataLine) continue;

          const jsonString = dataLine.replace(/^data:\s*/, "");
          try {
            const data = JSON.parse(jsonString);

            if (data.type === "answer_chunk") {
              currentText += data.content;
              if (data.workspace_id && !workspaceId) {
                setActiveWorkspaceId(data.workspace_id);
                fetchWorkspaces();
              }

              setMessages((prev) => {
                const updated = [...prev];
                updated[botMsgIndex] = {
                  ...updated[botMsgIndex],
                  text: currentText,
                  meta: "Generating...",
                };
                return updated;
              });
            }

            if (data.type === "metadata") {
              setMessages((prev) => {
                const updated = [...prev];
                updated[botMsgIndex] = {
                  ...updated[botMsgIndex],
                  citations: data.citations || [],
                  model: data.model || updated[botMsgIndex]?.model || null,
                  meta: data.timing
                    ? `Total ${formatSeconds(data.timing.total_seconds)}s · Retrieval ${formatSeconds(data.timing.retrieval_seconds)}s`
                    : "Completed",
                };
                return updated;
              });
              fetchWorkspaces();
            }
          } catch (err) {
            console.error("JSON Stream Parse Error:", err);
          }
        }
      }
    } catch (error) {
      console.error("Streaming error:", error);
      setMessages((prev) => {
        const updated = [...prev];
        updated[botMsgIndex] = {
          ...updated[botMsgIndex],
          text: "Failed to connect to the RAG engine. Please try again.",
          meta: "Error",
        };
        return updated;
      });
    } finally {
      setLoading(false);
    }
  };

  const handleRegenerate = async () => {
    if (loading || messages.length < 2) return;

    let botIndex = -1;
    for (let i = messages.length - 1; i >= 0; i -= 1) {
      if (messages[i].role === "bot") {
        botIndex = i;
        break;
      }
    }
    if (botIndex < 1 || messages[botIndex - 1]?.role !== "user") return;

    const userQuery = messages[botIndex - 1].text;
    let workspaceId = activeWorkspaceId;
    if (!workspaceId) {
      workspaceId = `ws-${crypto.randomUUID().slice(0, 12)}`;
      setActiveWorkspaceId(workspaceId);
      setActiveWorkspaceTitle("New chat");
    }

    await streamQuery(userQuery, workspaceId, { replaceBotIndex: botIndex });
  };

  const handleSend = async (e) => {
    e?.preventDefault();
    if (!input.trim() || loading) return;

    const userQuery = input.trim();
    setInput("");

    let workspaceId = activeWorkspaceId;
    if (!workspaceId) {
      workspaceId = `ws-${crypto.randomUUID().slice(0, 12)}`;
      setActiveWorkspaceId(workspaceId);
      setActiveWorkspaceTitle("New chat");
    }

    await streamQuery(userQuery, workspaceId);
  };

  const handleSuggestion = async (text) => {
    if (loading) return;
    setInput("");
    let workspaceId = activeWorkspaceId;
    if (!workspaceId) {
      workspaceId = `ws-${crypto.randomUUID().slice(0, 12)}`;
      setActiveWorkspaceId(workspaceId);
      setActiveWorkspaceTitle("New chat");
    }
    await streamQuery(text, workspaceId);
  };

  const handleCopy = async (text, idx) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedIndex(idx);
      setTimeout(() => setCopiedIndex(null), 1500);
    } catch {
      console.log("Copy failed");
    }
  };

  const filteredWorkspaces = workspaces.filter((item) =>
    item.title.toLowerCase().includes(search.toLowerCase())
  );

function FeedbackPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState(false);
  const [phone, setPhone] = useState(false);
  const [rating, setRating] = useState(0);
  const [type, setType] = useState("");
  const [message, setMessage] = useState("");
  const [file, setFile] = useState(null);
  const [submitted, setSubmitted] = useState(false);

  const resetForm = () => {
    setName("");
    setEmail(false);
    setPhone(false);
    setRating(0);
    setType("");
    setMessage("");
    setFile(null);
    setSubmitted(false);
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    if (!name.trim()) {
      alert("Please enter your name.");
      return;
    }

    if (!rating) {
      alert("Please select a rating.");
      return;
    }

    if (!type) {
      alert("Please select a feedback type.");
      return;
    }

    if (!message.trim()) {
      alert("Please enter your feedback.");
      return;
    }

    setSubmitted(true);
  };

  return (
    <div className="min-h-[calc(100vh-2rem)] flex items-start justify-center">
      <div className="w-full max-w-[900px] bg-[#303030] rounded-md shadow-xl overflow-hidden">
        {/* Feedback title bar */}
        <div className="h-11 bg-[#252525] flex items-center justify-center">
          <h1 className="text-white text-base sm:text-lg font-medium tracking-wide">
            Feedback
          </h1>
        </div>

        <form onSubmit={handleSubmit} className="p-4 sm:p-6 md:p-7 space-y-5">
          {/* Name */}
          <div>
            <div className="flex items-center gap-3">
              <label className="w-8 shrink-0 text-white text-xs sm:text-sm font-medium">
                Name
              </label>

              <div className="relative flex-1">
                <input
                  type="text"
                  value={name}
                  onChange={(e) => {
                    setName(e.target.value);
                    setSubmitted(false);
                  }}
                  className="w-full h-9 sm:h-10 rounded-md bg-[#f7f7f7] text-[#333] px-3 pr-9 text-xs sm:text-sm outline-none focus:ring-2 focus:ring-yellow-400"
                />
                <Pencil className="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
              </div>
            </div>
          </div>

          {/* Contact */}
          <div className="flex flex-wrap items-center gap-x-8 gap-y-3">
            <span className="w-8 text-white text-xs sm:text-sm font-medium">
              Contact
            </span>

            <label className="flex items-center gap-2 text-white text-[10px] sm:text-xs cursor-pointer">
              <input
                type="checkbox"
                checked={email}
                onChange={(e) => setEmail(e.target.checked)}
                className="w-3.5 h-3.5 accent-yellow-400 cursor-pointer"
              />
              Gmail
            </label>

            <label className="flex items-center gap-2 text-white text-[10px] sm:text-xs cursor-pointer">
              <input
                type="checkbox"
                checked={phone}
                onChange={(e) => setPhone(e.target.checked)}
                className="w-3.5 h-3.5 accent-yellow-400 cursor-pointer"
              />
              Phone number
            </label>
          </div>

          {/* Rating */}
          <div className="flex items-center gap-4">
            <span className="w-8 shrink-0" />

            <div className="flex items-center gap-2">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  type="button"
                  aria-label={`Rate ${star} star${star > 1 ? "s" : ""}`}
                  onClick={() => {
                    setRating(star);
                    setSubmitted(false);
                  }}
                  className="p-0.5 hover:scale-110 transition-transform"
                >
                  <Star
                    className={`w-4 h-4 sm:w-5 sm:h-5 ${
                      star <= rating
                        ? "fill-yellow-400 text-yellow-400"
                        : "text-yellow-400"
                    }`}
                  />
                </button>
              ))}
            </div>
          </div>

          {/* Type */}
          <div className="flex flex-wrap items-center gap-x-8 gap-y-3">
            <span className="w-8 text-white text-xs sm:text-sm font-medium">
              Type
            </span>

            {["Suggestion", "Bug", "Others"].map((item) => (
              <label
                key={item}
                className="flex items-center gap-2 text-white text-[10px] sm:text-xs cursor-pointer"
              >
                <input
                  type="radio"
                  name="feedback-type"
                  value={item}
                  checked={type === item}
                  onChange={(e) => {
                    setType(e.target.value);
                    setSubmitted(false);
                  }}
                  className="w-3.5 h-3.5 accent-yellow-400 cursor-pointer"
                />
                {item}
              </label>
            ))}
          </div>

          {/* Message */}
          <div>
            <textarea
              value={message}
              onChange={(e) => {
                setMessage(e.target.value);
                setSubmitted(false);
              }}
              placeholder=""
              className="w-full h-24 sm:h-28 md:h-32 resize-none rounded-md bg-[#f7f7f7] text-[#333] p-3 text-xs sm:text-sm outline-none focus:ring-2 focus:ring-yellow-400"
            />
          </div>

          {/* File upload */}
          <div className="flex flex-col sm:flex-row sm:items-center gap-3">
            <span className="text-white text-xs sm:text-sm font-medium">
              File
            </span>

            <label className="inline-flex items-center gap-2 w-full sm:w-[185px] h-9 rounded-md bg-[#f7f7f7] text-[#222] px-2.5 text-xs cursor-pointer hover:bg-white transition">
              <Upload className="w-4 h-4" />
              <span className="truncate">
                {file ? file.name : "Choose file"}
              </span>
              <input
                type="file"
                className="hidden"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
            </label>
          </div>

          {/* Success message */}
          {submitted && (
            <div className="rounded-md border border-green-400/40 bg-green-500/10 px-3 py-2 text-xs text-green-200">
              Feedback sent successfully.
            </div>
          )}

          {/* Actions */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-center gap-3 sm:gap-5 pt-1">
            <button
              type="submit"
              className="w-full sm:w-[225px] h-10 rounded-md bg-[#f2d331] hover:bg-[#e4c52a] active:scale-[0.99] text-white text-xs sm:text-sm font-medium transition flex items-center justify-center gap-2 shadow-sm"
            >
              <Upload className="w-4 h-4" />
              Send Feedback
            </button>

            <button
              type="button"
              onClick={resetForm}
              className="w-full sm:w-[125px] h-10 rounded-md bg-[#242424] hover:bg-[#1e1e1e] text-white text-xs sm:text-sm transition"
            >
              Cancel
            </button>
          </div>
        </form>
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
    <div className="relative flex h-screen w-screen overflow-hidden bg-[#f7f7f8] font-sans text-base text-gray-800 sm:text-lg">
      {sidebarOpen && (
        <div
          onClick={() => setSidebarOpen(false)}
          className="fixed inset-0 z-30 bg-black/50 transition-opacity lg:hidden"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-72 shrink-0 flex-col border-r border-gray-700 bg-[#2d2d2d] p-4 text-white transition-transform duration-300 ease-in-out lg:static lg:w-64 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        }`}
      >
        <div className="mb-5 flex items-center justify-between">
          <div className="flex items-center gap-2.5 text-base font-bold md:text-lg">
            <span className="text-xl" aria-hidden>
              🦝
            </span>
            <span>RAGcoon</span>
          </div>
          <button
            onClick={() => setSidebarOpen(false)}
            className="rounded p-1.5 text-gray-400 hover:bg-white/10 hover:text-white lg:hidden"
            aria-label="Close sidebar"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <button
          onClick={handleNewWorkspace}
          className="mb-4 flex w-full items-center justify-center gap-2 rounded-lg border border-dashed border-gray-600 bg-white/10 px-3 py-2.5 text-sm font-medium text-gray-100 transition hover:bg-white/20 hover:text-white md:text-base"
        >
          <MessageSquarePlus className="h-4 w-4" />
          <span>New chat</span>
        </button>

        <div className="relative mb-3">
          <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-400" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search chats..."
            className="h-9 w-full rounded-lg bg-white/10 pl-9 pr-3 text-sm text-white outline-none placeholder:text-gray-400 focus:ring-2 focus:ring-gray-500 md:text-base"
          />
        </div>

        <div className="min-h-0 flex-1 space-y-1 overflow-y-auto pr-1">
          <div className="mb-2 px-1 text-xs font-bold uppercase tracking-wider text-gray-400">
            Recents
          </div>
          {filteredWorkspaces.map((ws) => (
            <button
              key={ws.workspace_id}
              onClick={() => handleSelectWorkspace(ws)}
              className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm transition md:text-base ${
                activeWorkspaceId === ws.workspace_id
                  ? "bg-white/20 font-semibold text-white"
                  : "text-gray-300 hover:bg-white/10 hover:text-white"
              }`}
            >
              <ChevronRight className="h-3.5 w-3.5 shrink-0 text-gray-500" />
              <span className="truncate">{ws.title}</span>
            </button>
          ))}

          {filteredWorkspaces.length === 0 && (
            <div className="px-2 py-6 text-center text-sm text-gray-500">
              No chats yet. Start a new conversation.
            </div>
          )}
        </div>

        <div className="mt-4 space-y-1 border-t border-gray-700 pt-3">
          <Link
            to="/documents"
            className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-gray-300 transition hover:bg-white/10 hover:text-white md:text-base"
          >
            <FolderClosed className="h-4 w-4" />
            <span>Documents</span>
          </Link>
          <button
            onClick={() => setSidebarOpen(false)}
            className="hidden w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-gray-400 transition hover:bg-white/10 hover:text-white lg:flex md:text-base"
          >
            <PanelLeftClose className="h-4 w-4" />
            <span>Hide sidebar</span>
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
      <main className="flex-1 p-4 sm:p-6 md:p-8 overflow-y-auto">
        {activeTab === "Feedback" ? (
          <FeedbackPage />
        ) : (
          <div className="space-y-6">
        
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
            <div className="min-w-0">
              <h1 className="truncate text-base font-bold text-gray-900 md:text-lg">
                {activeWorkspaceTitle}
              </h1>
              <p className="hidden text-xs text-gray-400 sm:block sm:text-sm">
                Ask about CE senior project archives
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 rounded-full bg-gray-100 px-2.5 py-1 text-sm font-semibold text-gray-600">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-[#800000] text-[10px] font-bold text-white">
              G
            </span>
            <span className="hidden sm:inline">Guest</span>
          </div>
        </header>

        <section className="min-h-0 flex-1 overflow-y-auto px-3 py-6 sm:px-6">
          <div className="mx-auto w-full max-w-3xl">
            {showEmptyState ? (
              <div className="flex min-h-[60vh] flex-col items-center justify-center px-2 text-center">
                <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-[#2d2d2d] text-2xl shadow-sm">
                  🦝
                </div>
                <h2 className="text-xl font-bold text-gray-900 sm:text-2xl">
                  How can RAGcoon help?
                </h2>
                <p className="mt-2 max-w-md text-base text-gray-500">
                  Search and summarize Computer Engineering senior project documents with citations.
                </p>

                <div className="mt-8 grid w-full max-w-xl gap-2 sm:grid-cols-1">
                  {SUGGESTIONS.map((suggestion) => (
                    <button
                      key={suggestion}
                      onClick={() => handleSuggestion(suggestion)}
                      className="rounded-xl border border-gray-200 bg-white px-4 py-3 text-left text-base text-gray-700 shadow-sm transition hover:border-gray-300 hover:bg-gray-50"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="space-y-6">
                {messages.map((msg, index) => (
                  <div
                    key={index}
                    className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                    {msg.role === "user" ? (
                      <div className="max-w-[85%] sm:max-w-[75%]">
                        <div className="rounded-2xl rounded-tr-md bg-[#2d2d2d] px-4 py-3 text-sm leading-relaxed text-white shadow-sm sm:text-base">
                          {msg.text}
                        </div>
                      </div>
                    ) : (
                      <div className="flex w-full max-w-[95%] gap-3 sm:max-w-[90%]">
                        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gray-100 text-base shadow-sm">
                          🦝
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="rounded-2xl rounded-tl-md border border-gray-200 bg-[#fafafa] px-4 py-4 text-sm leading-relaxed text-gray-800 shadow-sm sm:px-5 sm:text-base">
                            <div className="whitespace-pre-wrap">
                              {msg.text || (
                                <span className="inline-flex items-center gap-2 text-gray-400">
                                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-gray-400" />
                                  Thinking...
                                </span>
                              )}
                            </div>
                          </div>

                          {(msg.text || (msg.citations && msg.citations.length > 0)) && (
                            <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-sm text-gray-400">
                              <div className="flex items-center gap-1">
                                <button
                                  onClick={() => handleCopy(msg.text, index)}
                                  className="rounded-md p-1.5 hover:bg-gray-100 hover:text-gray-700"
                                  title="Copy message"
                                  aria-label="Copy message"
                                >
                                  {copiedIndex === index ? (
                                    <Check className="h-3.5 w-3.5 text-green-600" />
                                  ) : (
                                    <Copy className="h-3.5 w-3.5" />
                                  )}
                                </button>

                                {index === lastBotIndex && !loading && (
                                  <button
                                    type="button"
                                    onClick={handleRegenerate}
                                    className="rounded-md p-1.5 hover:bg-gray-100 hover:text-gray-700"
                                    title="Regenerate answer"
                                    aria-label="Regenerate answer"
                                  >
                                    <RefreshCw className="h-3.5 w-3.5" />
                                  </button>
                                )}

                                {msg.citations && msg.citations.length > 0 && (
                                  <button
                                    onClick={() =>
                                      setShowCitationsIndex(
                                        showCitationsIndex === index ? null : index
                                      )
                                    }
                                    className="inline-flex items-center gap-1 rounded-md px-2 py-1 font-medium hover:bg-gray-100 hover:text-gray-700"
                                    title={`Sources (${msg.citations.length})`}
                                  >
                                    <FileText className="h-3.5 w-3.5" />
                                    Sources ({msg.citations.length})
                                  </button>
                                )}

                                <button
                                  onClick={() => setFeedback({ ...feedback, [index]: "like" })}
                                  className={`rounded-md p-1.5 hover:bg-gray-100 ${
                                    feedback[index] === "like" ? "text-green-600" : ""
                                  }`}
                                  aria-label="Like"
                                >
                                  <ThumbsUp className="h-3.5 w-3.5" />
                                </button>
                                <button
                                  onClick={() => setFeedback({ ...feedback, [index]: "dislike" })}
                                  className={`rounded-md p-1.5 hover:bg-gray-100 ${
                                    feedback[index] === "dislike" ? "text-red-600" : ""
                                  }`}
                                  aria-label="Dislike"
                                >
                                  <ThumbsDown className="h-3.5 w-3.5" />
                                </button>
                              </div>
                              <div className="flex flex-col items-end gap-0.5 text-right">
                                {msg.model && (
                                  <span className="text-xs text-gray-400">
                                    Model: {msg.model}
                                  </span>
                                )}
                                {msg.meta && (
                                  <span className="text-xs text-gray-400">{msg.meta}</span>
                                )}
                              </div>
                            </div>
                          )}

                          {showCitationsIndex === index &&
                            msg.citations &&
                            msg.citations.length > 0 && (
                              <div className="mt-3 space-y-2 rounded-xl border border-gray-200 bg-white p-3.5 text-sm text-gray-700 shadow-sm">
                                <div className="font-bold text-gray-900">Sources</div>
                                {msg.citations.map((c, i) => {
                                  const canPreview = Boolean(c.document_id);
                                  return (
                                    <div
                                      key={i}
                                      className="rounded-lg border border-gray-100 bg-gray-50 px-3 py-2"
                                    >
                                      <div className="flex items-start justify-between gap-2">
                                        <div className="min-w-0">
                                          <div className="font-semibold text-[#800000]">
                                            {c.project_title || c.source}
                                            {c.page ? (
                                              <span className="ml-1 font-normal text-gray-500">
                                                · page {c.page}
                                              </span>
                                            ) : null}
                                          </div>
                                          {c.content_snippet && (
                                            <p className="mt-1 line-clamp-3 text-gray-500 italic">
                                              "{c.content_snippet}"
                                            </p>
                                          )}
                                        </div>
                                        {canPreview ? (
                                          <button
                                            type="button"
                                            onClick={() =>
                                              openDocumentPreview(c.document_id, c.page)
                                            }
                                            className="inline-flex shrink-0 items-center gap-1 rounded-md border border-gray-200 bg-white px-2 py-1 text-xs font-semibold text-gray-700 hover:bg-gray-100"
                                            title="Open PDF preview"
                                          >
                                            <ExternalLink className="h-3.5 w-3.5" />
                                            Preview
                                          </button>
                                        ) : (
                                          <span className="shrink-0 text-xs text-gray-400">
                                            No file
                                          </span>
                                        )}
                                      </div>
                                    </div>
                                  );
                                })}
                              </div>
                            )}
                        </div>
                      </div>
                    )}
                  </div>
                ))}

                {loading && messages[messages.length - 1]?.role === "bot" && !messages[messages.length - 1]?.text && (
                  <div className="flex items-center gap-3 text-sm text-gray-500 sm:text-base">
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-100">
                      🦝
                    </div>
                    <div className="flex items-center gap-2 rounded-full border border-gray-200 bg-white px-3 py-1.5 shadow-sm">
                      <span className="flex gap-1">
                        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-gray-400 [animation-delay:-0.2s]" />
                        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-gray-400 [animation-delay:-0.1s]" />
                        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-gray-400" />
                      </span>
                      <span>Searching documents...</span>
                    </div>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>
            )}
          </div>
        </section>

        <div className="shrink-0 border-t border-gray-100 bg-white px-4 py-3 sm:px-6">
          <form
            onSubmit={handleSend}
            className="mx-auto flex max-w-3xl items-end gap-2 rounded-2xl border border-gray-200 bg-gray-50 px-3 py-2 shadow-sm transition focus-within:border-gray-400 focus-within:bg-white"
          >
            <textarea
              ref={inputRef}
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  if (!loading && input.trim()) {
                    handleSend(e);
                  }
                }
              }}
              disabled={loading}
              placeholder="Ask about a senior project..."
              className="max-h-40 min-h-[2.5rem] min-w-0 flex-1 resize-none overflow-y-auto bg-transparent px-2 py-2 text-sm leading-6 text-gray-800 outline-none placeholder:text-gray-400 sm:text-base"
              style={{ height: "2.5rem" }}
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className={`mb-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl transition ${
                loading || !input.trim()
                  ? "cursor-not-allowed bg-gray-200 text-gray-400"
                  : "bg-[#2d2d2d] text-white hover:bg-black active:scale-95"
              }`}
              aria-label="Send message"
            >
              <SendHorizontal className="h-4 w-4" />
            </button>
          </form>
          <div className="mt-2 text-center text-xs text-gray-400 sm:text-sm">
            Answers are grounded in uploaded senior project PDFs · Citations included when available
          </div>
        </div>
          </div>
        )}

      </main>
    </div>
  );
}
