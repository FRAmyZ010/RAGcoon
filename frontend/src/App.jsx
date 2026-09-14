import { useEffect, useRef, useState } from "react";


const initialBotMessage = {
  role: "bot",
  text: `The PLC (Programmable Logic Controller) is an industrial digital computer designed to automate control processes in machinery and production systems. It enables real-time monitoring and control by receiving input signals, processing them based on programmed logic, and generating corresponding outputs.

• Input Acquisition: The PLC collects signals from input devices such as sensors, switches, and buttons to determine the current state of the system.

• Logic Processing: The collected data is processed according to a predefined control program, written in Ladder Diagram (LD) or other PLC programming languages.

• Output Execution: Based on the processed logic, the PLC sends commands to output devices such as motors, relays, valves, or indicator lights.

• Continuous Operation (Scan Cycle): The PLC continuously repeats the cycle of input, processing, and output at high speed to ensure real-time system response.`,
  meta: "qwen2.5:7b-instruct - 30.52s (9.01 tok/s) - Mar 13, 1:09 AM",
};

const workspaces = [
  "ฐานข้อมูลไม่มีเอกสาร PLC",
  "ฐานข้อมูลเอกสารการทดลอง PLC",
  "สรุปเกี่ยวกับ PetFeeder",
  "Methodology ของ RAGcoon",
];

export default function App() {
  // =========================================================
  // CHAT STATE
  // =========================================================

  const [input, setInput] = useState("");

  const [messages, setMessages] = useState([initialBotMessage]);

  const [loading, setLoading] = useState(false);

  const [search, setSearch] = useState("");

  const [activeWorkspace, setActiveWorkspace] =
    useState("ฐานข้อมูลไม่มีเอกสาร PLC");

  // =========================================================
  // UI STATE
  // =========================================================

  const [showSettings, setShowSettings] = useState(false);

  const [showHeaderMenu, setShowHeaderMenu] = useState(false);

  const [showProfile, setShowProfile] = useState(false);

  const [showCitations, setShowCitations] = useState(false);

  const [showMore, setShowMore] = useState(false);

  const [sidebarOpen, setSidebarOpen] = useState(true);

  const [feedback, setFeedback] = useState(null);

  const [copied, setCopied] = useState(false);

  const chatEndRef = useRef(null);

  // =========================================================
  // AUTO SCROLL
  // =========================================================

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages, loading]);

  // =========================================================
  // SEND MESSAGE
  // =========================================================

  const handleSend = (e) => {
    e.preventDefault();

    if (!input.trim() || loading) return;

    const userQuery = input.trim();

    // User message
    setMessages((prev) => [
      ...prev,
      {
        role: "user",
        text: userQuery,
      },
    ]);

    setInput("");
    setLoading(true);

    // Mock RAG response
    setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        {
          role: "bot",
          text: `Based on the RAGcoon knowledge base:

Your question is "${userQuery}"

The system searched the selected document workspace and generated this response from the available project documents.

This is currently a frontend mock response. Later, this section can be connected to your FastAPI + Qdrant RAG backend.`,
          meta:
            "qwen2.5:7b-instruct - 1.2s - Mar 13, 1:10 AM",
        },
      ]);

      setLoading(false);
    }, 1000);
  };

  // =========================================================
  // NEW WORKSPACE
  // =========================================================

  const handleNewWorkspace = () => {
    const newName = prompt("ตั้งชื่อ Workspace ใหม่");

    if (!newName?.trim()) return;

    setActiveWorkspace(newName.trim());

    setMessages([]);

    setShowSettings(false);
  };

  // =========================================================
  // COPY
  // =========================================================

  const handleCopy = async (text) => {
    try {
      await navigator.clipboard.writeText(text);

      setCopied(true);

      setTimeout(() => {
        setCopied(false);
      }, 1500);
    } catch (error) {
      console.log("Copy failed");
    }
  };

  // =========================================================
  // REGENERATE
  // =========================================================

  const handleRegenerate = (index) => {
    const currentMessage = messages[index];

    if (!currentMessage) return;

    setLoading(true);

    setTimeout(() => {
      setMessages((prev) => {
        const updated = [...prev];

        updated[index] = {
          ...updated[index],
          text:
            updated[index].text +
            "\n\n[RAGcoon regenerated this response from the knowledge base.]",
        };

        return updated;
      });

      setLoading(false);
    }, 800);
  };

  // =========================================================
  // LOGOUT
  // =========================================================

  const handleLogout = () => {
    const confirmLogout = window.confirm(
      "คุณต้องการออกจากระบบหรือไม่?"
    );

    if (confirmLogout) {
      alert("Logout สำเร็จ");
    }
  };

  // =========================================================
  // FILTER WORKSPACES
  // =========================================================

  const filteredWorkspaces = workspaces.filter((item) =>
    item.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="min-h-screen w-full bg-[#858585] p-3 md:p-8 font-mono text-[12px]">

      {/* =====================================================
          APP CONTAINER
      ====================================================== */}

      <div className="mx-auto flex h-[calc(100vh-24px)] max-w-[1450px] overflow-hidden rounded-sm bg-white shadow-xl md:h-[calc(100vh-64px)]">

        {/* ===================================================
            SIDEBAR
        ==================================================== */}

        {sidebarOpen && (
          <aside className="flex w-[250px] shrink-0 flex-col justify-between bg-[#343434] px-3 py-3 text-white">

            {/* TOP SIDEBAR */}
            <div>

              {/* LOGO */}
              <div className="mb-4 flex items-center justify-between">

                <button
                  onClick={() => setShowHeaderMenu(!showHeaderMenu)}
                  className="flex items-center gap-2 rounded-md px-2 py-1 text-[14px] font-bold transition hover:bg-white/10"
                >
                  <span className="text-base">🦝</span>
                  <span>RAGcoon</span>
                </button>

                <button
                  onClick={() => setSidebarOpen(false)}
                  className="rounded p-1 text-gray-400 hover:bg-white/10 hover:text-white"
                  title="Close sidebar"
                >
                  ◀
                </button>
              </div>

              {/* SEARCH */}
              <div className="relative mb-4">

                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">
                  🔍
                </span>

                <input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search"
                  className="h-7 w-full rounded-full bg-white pl-8 pr-3 text-[11px] text-gray-800 outline-none placeholder:text-gray-400 focus:ring-2 focus:ring-gray-400"
                />

              </div>

              {/* NEW WORKSPACE */}
              <button
                onClick={handleNewWorkspace}
                className="mb-5 flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-gray-200 transition hover:bg-white/10 hover:text-white"
              >
                <span className="text-sm">✚</span>
                <span>New Workspace</span>
              </button>

              {/* RECENTS */}
              <div>

                <div className="mb-2 px-2 text-[10px] font-bold uppercase tracking-wider text-gray-500">
                  Recents
                </div>

                <div className="space-y-1">

                  {filteredWorkspaces.map((workspace, index) => (
                    <button
                      key={workspace}
                      onClick={() => {
                        setActiveWorkspace(workspace);

                        if (index === 0) {
                          setMessages([initialBotMessage]);
                        } else {
                          setMessages([]);
                        }
                      }}
                      className={`group flex w-full items-center justify-between rounded-md px-2 py-2 text-left transition ${
                        activeWorkspace === workspace
                          ? "bg-white/15 text-white"
                          : "text-gray-300 hover:bg-white/10 hover:text-white"
                      }`}
                    >

                      <span className="flex min-w-0 items-center gap-2">

                        <span className="text-[9px] text-gray-500">
                          {index === 0 ? "▸" : "└"}
                        </span>

                        <span className="truncate">
                          {workspace}
                        </span>

                      </span>

                      <span className="ml-2 text-gray-500 group-hover:text-white">
                        +
                      </span>

                    </button>
                  ))}

                  {filteredWorkspaces.length === 0 && (
                    <div className="px-2 py-3 text-[10px] text-gray-500">
                      No workspace found
                    </div>
                  )}

                </div>
              </div>

            </div>

            {/* SIDEBAR FOOTER */}
            <div className="space-y-2">

              {/* SETTINGS */}
              <button
                onClick={() => setShowSettings(!showSettings)}
                className="flex w-full items-center justify-between rounded-md px-2 py-2 text-gray-300 transition hover:bg-white/10 hover:text-white"
              >
                <span className="flex items-center gap-2">
                  ⚙ Settings
                </span>

                <span>
                  {showSettings ? "⌃" : "⌄"}
                </span>
              </button>

              {/* SETTINGS PANEL */}
              {showSettings && (
                <div className="rounded-md bg-[#292929] p-2 text-[10px] text-gray-300">

                  <button className="mb-1 w-full rounded px-2 py-1.5 text-left hover:bg-white/10">
                    Appearance
                  </button>

                  <button className="mb-1 w-full rounded px-2 py-1.5 text-left hover:bg-white/10">
                    RAG Configuration
                  </button>

                  <button className="w-full rounded px-2 py-1.5 text-left hover:bg-white/10">
                    Account
                  </button>

                </div>
              )}

              {/* LOGOUT */}
              <button
                onClick={handleLogout}
                className="flex w-full items-center justify-between rounded-md bg-white px-3 py-2 font-bold text-[#343434] transition hover:bg-gray-200 active:scale-[0.98]"
              >
                <span>Log Out</span>
                <span>↪</span>
              </button>

            </div>

          </aside>
        )}

        {/* ===================================================
            MAIN AREA
        ==================================================== */}

        <main className="relative flex min-w-0 flex-1 flex-col bg-white">

          {/* =================================================
              HEADER
          ================================================== */}

          <header className="flex h-[55px] shrink-0 items-center justify-between border-b border-gray-100 px-5">

            {/* LEFT */}
            <div className="relative">

              {!sidebarOpen && (
                <button
                  onClick={() => setSidebarOpen(true)}
                  className="mr-3 rounded-md px-2 py-1 hover:bg-gray-100"
                >
                  ☰
                </button>
              )}

              <button
                onClick={() =>
                  setShowHeaderMenu(!showHeaderMenu)
                }
                className="font-bold text-[#333] hover:text-black"
              >
                RAGcoon
                <span className="ml-1 text-[9px]">
                  {showHeaderMenu ? "▲" : "▼"}
                </span>
              </button>

              {/* HEADER DROPDOWN */}
              {showHeaderMenu && (
                <div className="absolute left-0 top-8 z-50 w-44 rounded-lg border border-gray-200 bg-white p-1 shadow-lg">

                  <button
                    onClick={() => setShowHeaderMenu(false)}
                    className="w-full rounded-md px-3 py-2 text-left text-[11px] hover:bg-gray-100"
                  >
                    Rename workspace
                  </button>

                  <button
                    onClick={() => setMessages([])}
                    className="w-full rounded-md px-3 py-2 text-left text-[11px] hover:bg-gray-100"
                  >
                    Clear conversation
                  </button>

                  <button
                    onClick={() => setShowHeaderMenu(false)}
                    className="w-full rounded-md px-3 py-2 text-left text-[11px] text-red-500 hover:bg-red-50"
                  >
                    Delete workspace
                  </button>

                </div>
              )}

            </div>

            {/* RIGHT */}
            <div className="relative flex items-center gap-3">

              <button
                onClick={() => alert("ไม่มีการแจ้งเตือนใหม่")}
                className="rounded-full p-1 hover:bg-gray-100"
                title="Notifications"
              >
                ♧
              </button>

              <button
                onClick={() => setShowProfile(!showProfile)}
                className="flex items-center gap-2 rounded-full px-2 py-1 hover:bg-gray-100"
              >

                <div className="flex h-6 w-6 items-center justify-center rounded-full bg-[#8c0808] text-[9px] font-bold text-white">
                  MJ
                </div>

                <span className="hidden text-[10px] font-bold text-gray-700 sm:block">
                  Marry Jann
                </span>

              </button>

              {/* PROFILE MENU */}
              {showProfile && (
                <div className="absolute right-0 top-10 z-50 w-40 rounded-lg border border-gray-200 bg-white p-2 shadow-lg">

                  <div className="border-b border-gray-100 px-2 py-2">
                    <div className="font-bold">
                      Marry Jann
                    </div>

                    <div className="text-[9px] text-gray-400">
                      General User
                    </div>
                  </div>

                  <button
                    onClick={() => alert("Open Profile")}
                    className="mt-1 w-full rounded px-2 py-2 text-left hover:bg-gray-100"
                  >
                    Profile
                  </button>

                  <button
                    onClick={() => setShowProfile(false)}
                    className="w-full rounded px-2 py-2 text-left hover:bg-gray-100"
                  >
                    Close
                  </button>

                </div>
              )}

            </div>

          </header>

          {/* =================================================
              CHAT
          ================================================== */}

          <section className="min-h-0 flex-1 overflow-y-auto">

            <div className="mx-auto w-full max-w-[820px] px-5 py-6">

              {/* ACTIVE WORKSPACE */}
              <div className="mb-8 text-center text-[9px] text-gray-400">
                {activeWorkspace}
              </div>

              {messages.map((msg, index) => (

                <div
                  key={index}
                  className={`mb-8 flex ${
                    msg.role === "user"
                      ? "justify-end"
                      : "justify-start"
                  }`}
                >

                  {/* ===============================
                      USER MESSAGE
                  ================================ */}

                  {msg.role === "user" ? (

                    <div className="max-w-[75%]">

                      <div className="mb-1 flex items-center justify-end gap-2">

                        <span className="text-[9px] text-gray-500">
                          Marry Jann
                        </span>

                        <div className="flex h-5 w-5 items-center justify-center rounded-full bg-[#8c0808] text-[7px] font-bold text-white">
                          MJ
                        </div>

                      </div>

                      <div className="rounded-2xl rounded-tr-md bg-[#dedede] px-4 py-2.5 text-[11px] leading-relaxed text-[#333]">
                        {msg.text}
                      </div>

                    </div>

                  ) : (

                    /* ===============================
                       BOT MESSAGE
                    ================================ */

                    <div className="flex w-full gap-3">

                      {/* RACCOON ICON */}
                      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gray-100 text-sm">
                        🦝
                      </div>

                      <div className="min-w-0 flex-1">

                        {/* BOT TEXT */}
                        <div className="rounded-2xl rounded-tl-md bg-[#dedede] px-5 py-4 text-[11px] leading-[1.55] text-[#333] shadow-sm">

                          <div className="whitespace-pre-wrap">
                            {msg.text}
                          </div>

                        </div>

                        {/* ACTION BAR */}
                        <div className="mt-2 flex items-center justify-between">

                          <div className="flex items-center gap-3 text-[11px] text-gray-400">

                            {/* COPY */}
                            <button
                              onClick={() =>
                                handleCopy(msg.text)
                              }
                              className="rounded p-1 hover:bg-gray-100 hover:text-gray-700"
                              title="Copy"
                            >
                              {copied ? "✓" : "▣"}
                            </button>

                            {/* ATTACHMENT */}
                            <button
                              onClick={() =>
                                alert("Citation document")
                              }
                              className="rounded p-1 hover:bg-gray-100 hover:text-gray-700"
                              title="Source"
                            >
                              📎
                            </button>

                            {/* REGENERATE */}
                            <button
                              onClick={() =>
                                handleRegenerate(index)
                              }
                              className="rounded p-1 hover:bg-gray-100 hover:text-gray-700"
                              title="Regenerate"
                            >
                              ↻
                            </button>

                            {/* LIKE */}
                            <button
                              onClick={() => setFeedback("like")}
                              className={`rounded p-1 hover:bg-gray-100 hover:text-gray-700 ${
                                feedback === "like"
                                  ? "text-green-600"
                                  : ""
                              }`}
                            >
                              ♡
                            </button>

                            {/* DISLIKE */}
                            <button
                              onClick={() => setFeedback("dislike")}
                              className={`rounded p-1 hover:bg-gray-100 hover:text-gray-700 ${
                                feedback === "dislike"
                                  ? "text-red-600"
                                  : ""
                              }`}
                            >
                              ♧
                            </button>

                            {/* MORE */}
                            <div className="relative">

                              <button
                                onClick={() =>
                                  setShowMore(!showMore)
                                }
                                className="rounded p-1 hover:bg-gray-100 hover:text-gray-700"
                              >
                                ⋮
                              </button>

                              {showMore && (
                                <div className="absolute bottom-7 left-0 z-30 w-32 rounded-lg border border-gray-200 bg-white p-1 shadow-lg">

                                  <button
                                    onClick={() =>
                                      alert("Report response")
                                    }
                                    className="w-full rounded px-2 py-2 text-left text-[10px] hover:bg-gray-100"
                                  >
                                    Report
                                  </button>

                                  <button
                                    onClick={() =>
                                      alert("Response saved")
                                    }
                                    className="w-full rounded px-2 py-2 text-left text-[10px] hover:bg-gray-100"
                                  >
                                    Save response
                                  </button>

                                </div>
                              )}

                            </div>

                          </div>

                          {/* META */}
                          {msg.meta && (
                            <span className="hidden text-[8px] text-gray-400 sm:block">
                              {msg.meta}
                            </span>
                          )}

                        </div>

                        {/* CITATIONS */}
                        <button
                          onClick={() =>
                            setShowCitations(!showCitations)
                          }
                          className="mt-2 text-[10px] text-gray-500 hover:text-gray-800"
                        >
                          Show citations{" "}
                          {showCitations ? "⌃" : "›"}
                        </button>

                        {showCitations && (
                          <div className="mt-2 rounded-lg border border-gray-200 bg-gray-50 p-3 text-[9px] text-gray-500">

                            <div className="font-bold text-gray-700">
                              Sources
                            </div>

                            <div className="mt-2">
                              📄 PLC_Project_Final.pdf
                            </div>

                            <div>
                              📄 PLC_Methodology.pdf
                            </div>

                            <div>
                              📄 Senior_Project_Database.pdf
                            </div>

                          </div>
                        )}

                      </div>

                    </div>

                  )}

                </div>

              ))}

              {/* LOADING */}
              {loading && (
                <div className="mb-5 flex items-center gap-3 text-[10px] text-gray-400">

                  <div className="flex h-7 w-7 items-center justify-center rounded-full bg-gray-100">
                    🦝
                  </div>

                  <div className="flex items-center gap-1">
                    <span>RAGcoon is searching</span>
                    <span className="animate-pulse">...</span>
                  </div>

                </div>
              )}

              <div ref={chatEndRef} />

            </div>

          </section>

          {/* =================================================
              INPUT
          ================================================== */}

          <div className="shrink-0 px-5 pb-5 pt-3">

            <form
              onSubmit={handleSend}
              className="mx-auto flex max-w-[720px] items-center rounded-full border border-gray-300 bg-[#dedede] px-4 py-1 shadow-sm focus-within:border-gray-400"
            >

              {/* INPUT */}
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={loading}
                placeholder="Ask anything"
                className="min-w-0 flex-1 bg-transparent px-2 py-2 text-[11px] text-gray-700 outline-none placeholder:text-gray-400"
              />

              {/* RIGHT BUTTONS */}
              <div className="flex items-center gap-2">

                {/* MICROPHONE */}
                <button
                  type="button"
                  onClick={() =>
                    alert("Microphone feature ยังไม่ได้เชื่อม Backend")
                  }
                  className="rounded-full p-1 text-gray-500 transition hover:bg-white hover:text-gray-800"
                  title="Voice input"
                >
                  🎙
                </button>

                {/* SEND */}
                <button
                  type="submit"
                  disabled={loading || !input.trim()}
                  className={`flex h-7 w-7 items-center justify-center rounded-full text-sm transition ${
                    loading || !input.trim()
                      ? "cursor-not-allowed text-gray-400"
                      : "bg-[#333] text-white hover:bg-black active:scale-90"
                  }`}
                  title="Send"
                >
                  ➤
                </button>

              </div>

            </form>

            <div className="mt-2 text-center text-[8px] text-gray-400">
              RAGcoon can make mistakes. Check important information.
            </div>

          </div>

        </main>

      </div>
      
      {/* TOAST */}
      {copied && (
        <div className="fixed bottom-5 left-1/2 -translate-x-1/2 rounded-full bg-[#333] px-4 py-2 text-[10px] text-white shadow-lg">
          Copied to clipboard
        </div>
      )}

    </div>
  );
}
