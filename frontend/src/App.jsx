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
  MessageSquare,
  MessageSquarePlus,
  PanelLeftClose,
  RefreshCw,
  Search,
  SendHorizontal,
  ThumbsDown,
  ThumbsUp,
  X,
} from "lucide-react";
import {
  loadChatThreads,
  removeChatThread,
  threadTitleFromMessages,
  toApiMessages,
  upsertChatThread,
} from "./services/chatHistory";
import { openDocumentPreview } from "./services/documentsApi";
import { submitFeedback } from "./services/feedbackApi";

const SUGGESTIONS = [
  "What senior projects used IoT or Bluetooth?",
  "List projects advised by Surapol",
  "Summarize projects about web applications",
];

function formatSeconds(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "0.00";
  return n.toFixed(2);
}

export default function App() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [threads, setThreads] = useState([]);
  const [activeWorkspaceId, setActiveWorkspaceId] = useState(null);
  const [activeWorkspaceTitle, setActiveWorkspaceTitle] = useState("New chat");
  const [showCitationsIndex, setShowCitationsIndex] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [feedback, setFeedback] = useState({});
  const [copiedIndex, setCopiedIndex] = useState(null);
  const [pendingDeleteId, setPendingDeleteId] = useState(null);

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
    const stored = loadChatThreads();
    setThreads(stored);
    const latest = stored[0];
    if (latest) {
      setActiveWorkspaceId(latest.id);
      setActiveWorkspaceTitle(latest.title);
      setMessages(latest.messages);
    }
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

  const openDraftChat = () => {
    setActiveWorkspaceId(null);
    setActiveWorkspaceTitle("New chat");
    setMessages([]);
    setShowCitationsIndex(null);
    setFeedback({});
    setPendingDeleteId(null);
    inputRef.current?.focus();
  };

  const handleSelectThread = (thread) => {
    setActiveWorkspaceId(thread.id);
    setActiveWorkspaceTitle(thread.title);
    setMessages(thread.messages);
    setShowCitationsIndex(null);
    setFeedback({});
    setPendingDeleteId(null);
    if (window.innerWidth < 1024) {
      setSidebarOpen(false);
    }
  };

  const handleDeleteThread = (threadId) => {
    setThreads((prev) => removeChatThread(prev, threadId));
    setPendingDeleteId(null);
    if (activeWorkspaceId === threadId) {
      openDraftChat();
    }
  };

  const persistSuccessfulThread = (workspaceId, nextMessages) => {
    const savedBot = nextMessages.some(
      (message) => message.role === "bot" && message.text.trim() && message.meta !== "Error"
    );
    if (!workspaceId || !savedBot) return;

    const thread = {
      id: workspaceId,
      title: threadTitleFromMessages(nextMessages),
      updatedAt: Date.now(),
      messages: nextMessages,
    };
    setThreads((prev) => upsertChatThread(prev, thread));
    setActiveWorkspaceTitle(thread.title);
  };

  const streamQuery = async (userQuery, workspaceId = activeWorkspaceId, options = {}) => {
    const { replaceBotIndex = null, priorMessages = messages } = options;
    setLoading(true);

    let snapshot;
    let botMsgIndex;
    if (replaceBotIndex != null) {
      botMsgIndex = replaceBotIndex;
      snapshot = priorMessages.map((message, index) =>
        index === botMsgIndex
          ? { role: "bot", text: "", citations: [], meta: "Searching...", model: null }
          : message
      );
    } else {
      botMsgIndex = priorMessages.length + 1;
      snapshot = [
        ...priorMessages,
        { role: "user", text: userQuery },
        { role: "bot", text: "", citations: [], meta: "Searching..." },
      ];
    }
    setMessages(snapshot);

    let saved = false;
    const historyForApi =
      replaceBotIndex != null ? priorMessages.slice(0, Math.max(replaceBotIndex - 1, 0)) : priorMessages;
    try {
      const response = await fetch("/api/v1/chat/query-stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query_text: userQuery,
          workspace_id: workspaceId,
          messages: toApiMessages(historyForApi),
        }),
      });

      if (!response.ok) {
        let message = `Chat stream failed (${response.status})`;
        try {
          const data = await response.json();
          if (typeof data?.detail === "string") message = data.detail;
        } catch {
          /* keep status message */
        }
        throw new Error(message);
      }
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
                workspaceId = data.workspace_id;
                setActiveWorkspaceId(data.workspace_id);
              }

              snapshot = snapshot.map((message, index) =>
                index === botMsgIndex
                  ? {
                      ...message,
                      text: currentText,
                      meta: "Generating...",
                      queryId: data.query_id ?? message.queryId ?? null,
                    }
                  : message
              );
              setMessages(snapshot);
            }

            if (data.type === "metadata") {
              snapshot = snapshot.map((message, index) =>
                index === botMsgIndex
                  ? {
                      ...message,
                      citations: data.citations || [],
                      queryId: data.query_id ?? message.queryId ?? null,
                      model: data.model || message?.model || null,
                      meta: data.timing
                        ? `Total ${formatSeconds(data.timing.total_seconds)}s · Retrieval ${formatSeconds(data.timing.retrieval_seconds)}s`
                        : "Completed",
                    }
                  : message
              );
              setMessages(snapshot);
              saved = true;
            }
          } catch (err) {
            console.error("JSON Stream Parse Error:", err);
          }
        }
      }
      if (saved || (currentText.trim() && response.ok)) {
        persistSuccessfulThread(workspaceId, snapshot);
      }
    } catch (error) {
      console.error("Streaming error:", error);
      snapshot = snapshot.map((message, index) =>
        index === botMsgIndex
          ? {
              ...message,
              text: error?.message || "Failed to connect to the RAG engine. Please try again.",
              meta: "Error",
            }
          : message
      );
      setMessages(snapshot);
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
    }

    await streamQuery(userQuery, workspaceId, {
      replaceBotIndex: botIndex,
      priorMessages: messages,
    });
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
    }

    await streamQuery(userQuery, workspaceId, { priorMessages: messages });
  };

  const handleSuggestion = async (text) => {
    if (loading) return;
    setInput("");
    let workspaceId = activeWorkspaceId;
    if (!workspaceId) {
      workspaceId = `ws-${crypto.randomUUID().slice(0, 12)}`;
      setActiveWorkspaceId(workspaceId);
    }
    await streamQuery(text, workspaceId, { priorMessages: messages });
  };

  const rateAnswer = async (index, kind) => {
    setFeedback({ ...feedback, [index]: kind });
    const queryId = messages[index]?.queryId;
    if (!queryId) return;
    try {
      await submitFeedback({
        name: "Anonymous",
        rating: kind === "like" ? 5 : 1,
        feedbackType: "Others",
        comment: kind,
        queryId,
      });
    } catch (err) {
      console.error(err);
    }
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

  const filteredThreads = threads.filter((item) =>
    item.title.toLowerCase().includes(search.toLowerCase())
  );

  const showEmptyState = messages.length === 0 && !loading;

  let lastBotIndex = -1;
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    if (messages[i].role === "bot") {
      lastBotIndex = i;
      break;
    }
  }

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
          onClick={openDraftChat}
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
          {filteredThreads.map((thread) => (
            <div key={thread.id}>
              <div
                className={`flex w-full items-center gap-1 rounded-lg pr-1 text-sm transition md:text-base ${
                  activeWorkspaceId === thread.id
                    ? "bg-white/20 font-semibold text-white"
                    : "text-gray-300 hover:bg-white/10 hover:text-white"
                }`}
              >
                <button
                  type="button"
                  onClick={() => handleSelectThread(thread)}
                  className="flex min-w-0 flex-1 items-center gap-2 px-3 py-2 text-left"
                >
                  <ChevronRight className="h-3.5 w-3.5 shrink-0 text-gray-500" />
                  <span className="truncate">{thread.title}</span>
                </button>
                <button
                  type="button"
                  onClick={() => setPendingDeleteId(thread.id)}
                  className="shrink-0 rounded p-1 text-gray-400 hover:bg-white/10 hover:text-white"
                  aria-label={`Delete ${thread.title}`}
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
              {pendingDeleteId === thread.id && (
                <div className="mb-1 mt-1 flex items-center justify-between gap-2 rounded-lg bg-black/20 px-3 py-2 text-xs text-gray-200">
                  <span>ลบแชทนี้?</span>
                  <span className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setPendingDeleteId(null)}
                      className="rounded px-2 py-1 hover:bg-white/10"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDeleteThread(thread.id)}
                      className="rounded px-2 py-1 text-red-300 hover:bg-white/10"
                    >
                      Delete
                    </button>
                  </span>
                </div>
              )}
            </div>
          ))}

          {filteredThreads.length === 0 && (
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
          <Link
            to="/feedback"
            className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-gray-300 transition hover:bg-white/10 hover:text-white md:text-base"
          >
            <MessageSquare className="h-4 w-4" />
            <span>Feedback</span>
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

      <main className="flex h-full min-w-0 flex-1 flex-col bg-white">
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-gray-200 bg-white/90 px-4 backdrop-blur md:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="rounded-lg p-1.5 text-gray-700 hover:bg-gray-100"
              title="Toggle sidebar"
            >
              <Menu className="h-5 w-5" />
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

          <div className="flex items-center gap-2">
            <Link
              to="/feedback"
              className="inline-flex items-center gap-1.5 rounded-full border border-gray-200 px-3 py-1.5 text-sm font-semibold text-gray-700 hover:bg-gray-100"
            >
              <MessageSquare className="h-4 w-4" />
              <span>Feedback</span>
            </Link>
            <div className="flex items-center gap-2 rounded-full bg-gray-100 px-2.5 py-1 text-sm font-semibold text-gray-600">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-[#800000] text-[10px] font-bold text-white">
                G
              </span>
              <span className="hidden sm:inline">Guest</span>
            </div>
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
                                  onClick={() => rateAnswer(index, "like")}
                                  className={`rounded-md p-1.5 hover:bg-gray-100 ${
                                    feedback[index] === "like" ? "text-green-600" : ""
                                  }`}
                                  aria-label="Like"
                                >
                                  <ThumbsUp className="h-3.5 w-3.5" />
                                </button>
                                <button
                                  onClick={() => rateAnswer(index, "dislike")}
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
      </main>
    </div>
  );
}
