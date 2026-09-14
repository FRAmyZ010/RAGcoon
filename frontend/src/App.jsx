import { useEffect, useRef, useState } from "react";

export default function App() {
  // =========================================================
  // STATE MANAGEMENT
  // =========================================================
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [workspaces, setWorkspaces] = useState([]);
  const [activeWorkspaceId, setActiveWorkspaceId] = useState(null);
  const [activeWorkspaceTitle, setActiveWorkspaceTitle] = useState("New Workspace");

  // UI Responsive & Menu States
  const [showSettings, setShowSettings] = useState(false);
  const [showProfile, setShowProfile] = useState(false);
  const [showCitationsIndex, setShowCitationsIndex] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false); // ปิดใน Mobile เป็น Default
  const [feedback, setFeedback] = useState({});
  const [copiedIndex, setCopiedIndex] = useState(null);

  const chatEndRef = useRef(null);

  // =========================================================
  // INITIAL SETUP: LOAD WORKSPACES ONLY (NO AUTO-NEW WORKSPACE)
  // =========================================================
  useEffect(() => {
    fetchWorkspaces();
    // นำ handleNewWorkspace(); ออกจากตรงนี้ เพื่อไม่ให้สร้างแชทใหม่อัตโนมัติเมื่อเปิดหน้าแรก

    // Auto Open Sidebar บนหน้าจอ Desktop
    if (window.innerWidth >= 1024) {
      setSidebarOpen(true);
    }
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const fetchWorkspaces = async () => {
    try {
      const res = await fetch("/api/v1/chat/workspaces");
      if (res.ok) {
        const data = await res.json();
        setWorkspaces(data);
      }
    } catch (err) {
      console.error("Failed to load workspaces:", err);
    }
  };

  const handleNewWorkspace = () => {
    const newWorkspaceId = `ws-${crypto.randomUUID().slice(0, 12)}`;
    setActiveWorkspaceId(newWorkspaceId);
    setActiveWorkspaceTitle("New Workspace");
    setMessages([
      {
        role: "bot",
        text: "Hi! I am RAGcoon AI Assistant 🦝 . I am ready to help searching for CE senior project",
        meta: "RAGcoon Engine Ready",
        citations: [],
      },
    ]);
  };

  const handleSelectWorkspace = async (ws) => {
    setActiveWorkspaceId(ws.workspace_id);
    setActiveWorkspaceTitle(ws.title);
    setLoading(true);

    // บนหน้าจอมือถือ ให้ปิด Sidebar หลังเลือกห้องแชท
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
              ? `Total: ${q.retrieved_docs.timing.total_seconds}s`
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

  // =========================================================
  // SSE REAL-TIME STREAMING QUERY HANDLER
  // =========================================================
  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userQuery = input.trim();
    setInput("");

    setMessages((prev) => [...prev, { role: "user", text: userQuery }]);
    setLoading(true);

    const botMsgIndex = messages.length + 1;
    setMessages((prev) => [
      ...prev,
      {
        role: "bot",
        text: "",
        citations: [],
        meta: "Searching...",
      },
    ]);

    try {
      const response = await fetch("/api/v1/chat/query-stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query_text: userQuery,
          workspace_id: activeWorkspaceId,
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
              if (data.workspace_id && !activeWorkspaceId) {
                setActiveWorkspaceId(data.workspace_id);
                fetchWorkspaces();
              }

              setMessages((prev) => {
                const updated = [...prev];
                updated[botMsgIndex] = {
                  ...updated[botMsgIndex],
                  text: currentText,
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
                  meta: data.timing
                    ? `Total: ${data.timing.total_seconds || 0}s | Retrieval: ${data.timing.retrieval_seconds || 0}s`
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
          text: "Failed to connect RAG Engine. Please try again!",
        };
        return updated;
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async (text, idx) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedIndex(idx);
      setTimeout(() => setCopiedIndex(null), 1500);
    } catch (error) {
      console.log("Copy failed");
    }
  };

  const filteredWorkspaces = workspaces.filter((item) =>
    item.title.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="flex h-screen w-screen bg-white font-sans text-sm overflow-hidden relative">
      {/* MOBILE BACKDROP OVERLAY */}
      {sidebarOpen && (
        <div
          onClick={() => setSidebarOpen(false)}
          className="fixed inset-0 bg-black/50 z-30 lg:hidden transition-opacity"
        />
      )}

      {/* ===================================================
          SIDEBAR (RESPONSIVE DRAWER)
      ==================================================== */}
      <aside
        className={`fixed lg:static inset-y-0 left-0 z-40 flex w-72 lg:w-64 shrink-0 flex-col justify-between bg-[#2d2d2d] p-4 text-white transition-transform duration-300 ease-in-out border-r border-gray-700 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        }`}
      >
        <div className="flex flex-col h-full min-h-0">
          {/* BRAND HEADER */}
          <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-2.5 font-bold text-base md:text-lg">
              <span className="text-xl">🦝</span>
              <span>RAGcoon</span>
            </div>
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden rounded p-1.5 text-gray-400 hover:bg-white/10 hover:text-white"
            >
              ✕
            </button>
          </div>

          {/* SEARCH BOX */}
          <div className="relative mb-3">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-xs">🔍</span>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search Workspaces..."
              className="h-9 w-full rounded-lg bg-white/10 pl-9 pr-3 text-xs md:text-sm text-white outline-none placeholder:text-gray-400 focus:ring-2 focus:ring-gray-500"
            />
          </div>

          {/* NEW WORKSPACE BUTTON */}
          <button
            onClick={handleNewWorkspace}
            className="mb-4 flex w-full items-center justify-center gap-2 rounded-lg bg-white/10 px-3 py-2 text-xs md:text-sm font-medium text-gray-200 transition hover:bg-white/20 hover:text-white border border-dashed border-gray-600"
          >
            <span className="text-base">+</span>
            <span>New Workspace</span>
          </button>

          {/* RECENTS LIST */}
          <div className="flex-1 overflow-y-auto min-h-0 space-y-1 pr-1">
            <div className="mb-2 px-1 text-[11px] font-bold uppercase tracking-wider text-gray-400">
              Recents
            </div>
            {filteredWorkspaces.map((ws) => (
              <button
                key={ws.workspace_id}
                onClick={() => handleSelectWorkspace(ws)}
                className={`flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-xs md:text-sm transition ${
                  activeWorkspaceId === ws.workspace_id
                    ? "bg-white/20 font-semibold text-white"
                    : "text-gray-300 hover:bg-white/10 hover:text-white"
                }`}
              >
                <span className="flex min-w-0 items-center gap-2">
                  <span className="text-gray-500 text-xs">▸</span>
                  <span className="truncate">{ws.title}</span>
                </span>
              </button>
            ))}

            {filteredWorkspaces.length === 0 && (
              <div className="px-2 py-4 text-center text-xs text-gray-500">
                No recent workspace found
              </div>
            )}
          </div>
        </div>

        {/* SIDEBAR FOOTER */}
        {/* <div className="mt-4 pt-3 border-t border-gray-700 space-y-2">
          <button
            onClick={() => setShowSettings(!showSettings)}
            className="flex w-full items-center justify-between rounded-lg px-3 py-2 text-xs md:text-sm text-gray-300 hover:bg-white/10 hover:text-white"
          >
            <span className="flex items-center gap-2">⚙ Settings</span>
            <span>{showSettings ? "▲" : "▼"}</span>
          </button>

          {showSettings && (
            <div className="rounded-lg bg-[#222222] p-2 text-xs text-gray-300 space-y-1">
              <button className="w-full rounded px-2 py-1.5 text-left hover:bg-white/10">Appearance</button>
              <button className="w-full rounded px-2 py-1.5 text-left hover:bg-white/10">RAG Configuration</button>
            </div>
          )}

          <button
            onClick={() => window.confirm("คุณต้องการออกจากระบบหรือไม่?") && alert("Logout สำเร็จ")}
            className="flex w-full items-center justify-between rounded-lg bg-white px-3 py-2 text-xs md:text-sm font-bold text-[#2d2d2d] transition hover:bg-gray-200"
          >
            <span>Log Out</span>
            <span>↪</span>
          </button>
        </div> */}
      </aside>

      {/* ===================================================
          MAIN CONTENT AREA
      ==================================================== */}
      <main className="flex flex-1 flex-col h-full min-w-0 bg-white">
        {/* HEADER TOP BAR */}
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-gray-200 px-4 md:px-6 bg-white">
          <div className="flex items-center gap-3 min-w-0">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="rounded-lg p-1.5 hover:bg-gray-100 text-gray-700"
              title="Toggle Sidebar"
            >
              ☰
            </button>
            <h1 className="font-bold text-sm md:text-base text-gray-800 truncate">
              {activeWorkspaceTitle}
            </h1>
          </div>

          {/* USER PROFILE */}
          <div className="relative flex items-center gap-3 shrink-0">
            <button
              onClick={() => setShowProfile(!showProfile)}
              className="flex items-center gap-2 rounded-full p-1 hover:bg-gray-100"
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#800000] text-xs font-bold text-white shadow-sm">
                MJ
              </div>
              <span className="hidden text-xs md:text-sm font-semibold text-gray-700 sm:block">
                Marry Jann
              </span>
            </button>

            {showProfile && (
              <div className="absolute right-0 top-12 z-50 w-44 rounded-xl border border-gray-200 bg-white p-2 shadow-xl text-xs">
                <div className="border-b border-gray-100 px-3 py-2">
                  <div className="font-bold text-gray-800">Marry Jann</div>
                  <div className="text-gray-400">General User</div>
                </div>
                <button onClick={() => setShowProfile(false)} className="mt-1 w-full rounded-md px-3 py-2 text-left hover:bg-gray-100">
                  Profile
                </button>
                <button onClick={() => setShowProfile(false)} className="w-full rounded-md px-3 py-2 text-left hover:bg-gray-100 text-red-600">
                  Close
                </button>
              </div>
            )}
          </div>
        </header>

        {/* CHAT MESSAGES PANEL */}
        <section className="flex-1 overflow-y-auto px-3 sm:px-6 py-6 min-h-0">
          <div className="mx-auto w-full max-w-3xl space-y-6">
            {messages.map((msg, index) => (
              <div
                key={index}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                {msg.role === "user" ? (
                  /* USER BUBBLE */
                  <div className="max-w-[85%] sm:max-w-[75%]">
                    <div className="mb-1 flex items-center justify-end gap-1.5 text-xs text-gray-500">
                      <span>Marry Jann</span>
                      <div className="flex h-5 w-5 items-center justify-center rounded-full bg-[#800000] text-[10px] font-bold text-white">
                        MJ
                      </div>
                    </div>
                    <div className="rounded-2xl rounded-tr-sm bg-[#e9ecef] px-4 py-3 text-xs sm:text-sm leading-relaxed text-gray-800 shadow-sm">
                      {msg.text}
                    </div>
                  </div>
                ) : (
                  /* BOT BUBBLE */
                  <div className="flex w-full gap-3 max-w-[95%] sm:max-w-[90%]">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gray-100 text-lg shadow-sm">
                      🦝
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="rounded-2xl rounded-tl-sm bg-gray-50 border border-gray-200 px-4 sm:px-5 py-4 text-xs sm:text-sm leading-relaxed text-gray-800 shadow-sm">
                        <div className="whitespace-pre-wrap">{msg.text || "Thinking . . ."}</div>
                      </div>

                      {/* ACTION BAR */}
                      <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-xs text-gray-400">
                        <div className="flex items-center gap-3">
                          <button
                            onClick={() => handleCopy(msg.text, index)}
                            className="rounded p-1 hover:bg-gray-100 hover:text-gray-700"
                            title="Copy message"
                          >
                            {copiedIndex === index ? "✓ Copied" : "▣ Copy"}
                          </button>
                          {msg.citations && msg.citations.length > 0 && (
                            <button
                              onClick={() =>
                                setShowCitationsIndex(showCitationsIndex === index ? null : index)
                              }
                              className="rounded p-1 hover:bg-gray-100 hover:text-gray-700 font-medium"
                            >
                              📎 Citations ({msg.citations.length})
                            </button>
                          )}
                          <button
                            onClick={() => setFeedback({ ...feedback, [index]: "like" })}
                            className={`rounded p-1 hover:bg-gray-100 ${feedback[index] === "like" ? "text-green-600 font-bold" : ""}`}
                          >
                            👍
                          </button>
                          <button
                            onClick={() => setFeedback({ ...feedback, [index]: "dislike" })}
                            className={`rounded p-1 hover:bg-gray-100 ${feedback[index] === "dislike" ? "text-red-600 font-bold" : ""}`}
                          >
                            👎
                          </button>
                        </div>
                        {msg.meta && <span className="text-[11px] text-gray-400">{msg.meta}</span>}
                      </div>

                      {/* CITATIONS SECTION */}
                      {showCitationsIndex === index && msg.citations && msg.citations.length > 0 && (
                        <div className="mt-3 rounded-xl border border-gray-200 bg-white p-3.5 text-xs text-gray-700 shadow-sm">
                          <div className="font-bold text-gray-900 mb-2">📄 เอกสารอ้างอิง (Citations):</div>
                          <ul className="list-disc pl-4 space-y-1.5">
                            {msg.citations.map((c, i) => (
                              <li key={i}>
                                <span className="font-semibold text-blue-700">{c.project_title || c.source}</span>
                                {c.page && ` (หน้า ${c.page})`}
                                {c.content_snippet && (
                                  <p className="text-gray-500 italic mt-0.5 text-xs">"{c.content_snippet}"</p>
                                )}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div className="flex items-center gap-3 text-xs sm:text-sm text-gray-500">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-100">🦝</div>
                <div className="flex items-center gap-1">
                  <span>RAGcoon are searching for documents!</span>
                  <span className="animate-pulse">...</span>
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>
        </section>

        {/* INPUT FORM (BOTTOM) */}
        <div className="shrink-0 px-4 py-3 sm:px-6 border-t border-gray-100 bg-white">
          <form
            onSubmit={handleSend}
            className="mx-auto flex max-w-3xl items-center rounded-full border border-gray-300 bg-gray-100 px-4 py-1.5 shadow-sm focus-within:border-gray-500 focus-within:bg-white transition"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={loading}
              placeholder="Ask RAGcoon"
              className="min-w-1 flex-1 bg-transparent px-2 py-1.5 text-xs sm:text-sm text-gray-800 outline-none placeholder:text-gray-400"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-bold transition ${
                loading || !input.trim()
                  ? "cursor-not-allowed text-gray-400 bg-gray-200"
                  : "bg-[#2d2d2d] text-white hover:bg-black active:scale-95"
              }`}
            >
              ➤
            </button>
          </form>
          <div className="mt-2 text-center text-[10px] sm:text-xs text-gray-400">
            RAGcoon Search Engine - Powered by FastAPI & Vector Qdrant
          </div>
        </div>
      </main>
    </div>
  );
}