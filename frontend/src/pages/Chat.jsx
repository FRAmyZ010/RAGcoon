import { useState, useRef, useEffect } from "react";
import { Link } from "react-router-dom";

export default function App() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([
    { 
      role: "bot", 
      text: "สวัสดีครับ! ผมคือ RAGcoon AI Assistant 🦝 พร้อมช่วยค้นหาและตอบคำถามของคุณแล้วครับ",
      meta: "RAGcoon Engine v1.0"
    }
  ]);
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef(null);

  // เลื่อนลงล่างสุดอัตโนมัติเมื่อมีข้อความใหม่
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ฟังก์ชันจำลองการตอบกลับ (Mock Response ฝั่ง Frontend)
  const handleSend = (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userQuery = input;

    // 1. แสดงคำถามของ User ทันที
    setMessages((prev) => [...prev, { role: "user", text: userQuery }]);
    setInput("");
    setLoading(true);

    // 2. จำลองเวลาการประมวลผล 1 วินาที
    setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        {
          role: "bot",
          text: `[RAGcoon Response] คำถามของคุณคือ: "${userQuery}" (ระบบกำลังดึงข้อมูลจาก Knowledge Base)`,
          meta: "RAGcoon Engine v1.0"
        },
      ]);
      setLoading(false);
    }, 1000);
  };

  return (
    <div style={{ display: "flex", height: "100vh", backgroundColor: "#828282", fontFamily: "monospace", fontSize: "12px", overflow: "hidden" }}>
      
      {/* ---------------- 1. SIDEBAR ---------------- */}
      <div style={{ width: "240px", backgroundColor: "#353535", color: "#ffffff", padding: "16px", display: "flex", flexDirection: "column", justifyContent: "space-between", flexShrink: 0 }}>
        <div>
          {/* Logo Brand */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", fontWeight: "bold", fontSize: "15px" }}>
              <span>🦝</span> RAGcoon
            </div>
            <Link to="/documents" title="Go to Documents" style={{ color: "#ffffff", textDecoration: "none", opacity: 0.6, fontSize: "12px", cursor: "pointer" }}>
              📎
            </Link>
          </div>

          {/* Search Box */}
          <div style={{ marginBottom: "14px" }}>
            <input 
              type="text" 
              placeholder="Search" 
              style={{ width: "100%", padding: "6px 12px", borderRadius: "16px", border: "none", outline: "none", fontSize: "11px", backgroundColor: "#ffffff", color: "#000", boxSizing: "border-box" }}
            />
          </div>

          {/* New Workspace Button */}
          <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "#d1d5db", cursor: "pointer", marginBottom: "16px" }}>
            <span>+</span> New Workspace
          </div>

          {/* Recents Menu */}
          <div>
            <div style={{ color: "#9ca3af", fontSize: "11px", fontWeight: "bold", marginBottom: "8px" }}>Recents</div>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px", color: "#e5e7eb" }}>
              <div style={{ display: "flex", justifyContent: "space-between", cursor: "pointer" }}>
                <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>Equipment used in PLC project</span>
                <span>+</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "4px", paddingLeft: "6px", color: "#ffffff", backgroundColor: "rgba(255, 255, 255, 0.15)", padding: "4px 8px", borderRadius: "4px" }}>
                <span style={{ opacity: 0.5 }}>└</span>
                <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>PLC Workflow Summary</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", cursor: "pointer" }}>
                <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>PetFeeder Overview</span>
                <span>+</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", cursor: "pointer" }}>
                <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>RAGcoon Methodology</span>
                <span>+</span>
              </div>
            </div>
          </div>
        </div>

        {/* Sidebar Footer */}
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", cursor: "pointer", color: "#d1d5db" }}>
            <span>⚙ Settings</span>
            <span>∨</span>
          </div>
          <button style={{ width: "100%", backgroundColor: "#ffffff", color: "#353535", fontWeight: "bold", padding: "8px 12px", borderRadius: "8px", border: "none", cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span>Log Out</span>
            <span>↪</span>
          </button>
        </div>
      </div>

      {/* ---------------- 2. MAIN CHAT AREA ---------------- */}
      <div style={{ flex: 1, backgroundColor: "#ffffff", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
        
        {/* Header Top Bar */}
        <div style={{ padding: "12px 24px", borderBottom: "1px solid #f3f4f6", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ fontWeight: "bold", fontSize: "13px", color: "#353535", cursor: "pointer" }}>
            RAGcoon ∨
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <div style={{ width: "26px", height: "26px", borderRadius: "50%", backgroundColor: "#800000", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "10px", fontWeight: "bold" }}>
              MJ
            </div>
            <span style={{ fontWeight: "bold", color: "#353535" }}>Marry Jann</span>
          </div>
        </div>

        {/* --- ส่วนกล่องแสดงผลข้อความแชท (นำจากโค้ดล่างมาใส่) --- */}
        <div style={{
          flex: 1,
          overflowY: "auto",
          padding: "20px",
          maxWidth: "800px",
          width: "100%",
          margin: "0 auto",
          boxSizing: "border-box"
        }}>
          {messages.map((msg, index) => (
            <div
              key={index}
              style={{
                marginBottom: "16px",
                textAlign: msg.role === "user" ? "right" : "left"
              }}
            >
              <div style={{
                display: "inline-block",
                padding: "12px 18px",
                borderRadius: msg.role === "user" ? "18px 18px 4px 18px" : "18px 18px 18px 4px",
                backgroundColor: msg.role === "user" ? "#4f46e5" : "#f8fafc",
                color: msg.role === "user" ? "#ffffff" : "#1e293b",
                border: msg.role === "user" ? "none" : "1px solid #e2e8f0",
                maxWidth: "75%",
                wordBreak: "break-word",
                lineHeight: "1.5",
                boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
                textAlign: "left"
              }}>
                <div>{msg.text}</div>
                {msg.meta && (
                  <div style={{ fontSize: "10px", opacity: 0.6, marginTop: "6px", textAlign: "right" }}>
                    {msg.meta}
                  </div>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div style={{ color: "#64748b", fontStyle: "italic", fontSize: "12px", display: "flex", alignItems: "center", gap: "6px" }}>
              <span>🦝</span> RAGcoon กำลังค้นหาข้อมูลและประมวลผลคำตอบ...
            </div>
          )}

          <div ref={chatEndRef} />
        </div>

        {/* --- ส่วนช่องพิมพ์คำถาม --- */}
        <div style={{ padding: "20px 40px", maxWidth: "800px", width: "100%", margin: "0 auto", boxSizing: "border-box" }}>
          <form onSubmit={handleSend} style={{ display: "flex", gap: "10px", position: "relative" }}>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask anything"
              disabled={loading}
              style={{
                flex: 1,
                padding: "12px 90px 12px 20px",
                borderRadius: "24px",
                border: "none",
                backgroundColor: "#e8e8e8",
                color: "#353535",
                fontSize: "12px",
                outline: "none"
              }}
            />
            <div style={{ position: "absolute", right: "16px", top: "50%", transform: "translateY(-50%)", display: "flex", gap: "10px", alignItems: "center", color: "#6b7280" }}>
              <span style={{ cursor: "pointer" }}>🎙️</span>
              <button
                type="submit"
                disabled={loading || !input.trim()}
                style={{
                  border: "none",
                  backgroundColor: "transparent",
                  color: loading || !input.trim() ? "#cbd5e1" : "#4f46e5",
                  fontWeight: "bold",
                  cursor: loading || !input.trim() ? "not-allowed" : "pointer",
                  fontSize: "14px"
                }}
              >
                ➔
              </button>
            </div>
          </form>
        </div>

      </div>
    </div>
  );
}