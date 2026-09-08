import { useState, useRef, useEffect } from "react";

export default function Chat() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([
    { 
      role: "bot", 
      text: "สวัสดีครับ! ผมคือ RAGcoon AI Assistant 🦝 พร้อมช่วยค้นหาและตอบคำถามของคุณแล้วครับ" 
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
    <div style={{ maxWidth: "720px", margin: "40px auto", fontFamily: "sans-serif" }}>
      {/* ส่วนหัวแบรนด์ RAGcoon */}
      <div style={{ textAlign: "center", marginBottom: "25px" }}>
        <h2 style={{ color: "#2c3e50", margin: "0 0 5px 0", display: "flex", alignItems: "center", justifyContent: "center", gap: "8px" }}>
          🦝 RAGcoon AI
        </h2>
        <span style={{ fontSize: "13px", color: "#7f8c8d" }}>
          Minimalist RAG-powered Chat Interface
        </span>
      </div>

      {/* กล่องแสดงผลแชท */}
      <div style={{
        border: "1px solid #e2e8f0",
        height: "460px",
        overflowY: "auto",
        padding: "20px",
        borderRadius: "16px",
        backgroundColor: "#f8fafc",
        boxShadow: "0 4px 12px rgba(0, 0, 0, 0.03)",
        marginBottom: "20px"
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
              backgroundColor: msg.role === "user" ? "#4f46e5" : "#ffffff", // สีม่วงครามสำหรับ User
              color: msg.role === "user" ? "#ffffff" : "#1e293b",
              border: msg.role === "user" ? "none" : "1px solid #e2e8f0",
              maxWidth: "75%",
              wordBreak: "break-word",
              lineHeight: "1.5",
              boxShadow: "0 1px 3px rgba(0,0,0,0.05)"
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
          <div style={{ color: "#64748b", fontStyle: "italic", fontSize: "14px", display: "flex", alignItems: "center", gap: "6px" }}>
            <span>🦝</span> RAGcoon กำลังค้นหาข้อมูลและประมวลผลคำตอบ...
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      {/* ช่องพิมพ์คำถาม */}
      <form onSubmit={handleSend} style={{ display: "flex", gap: "10px" }}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="พิมพ์คำถามเพื่อค้นหาด้วย RAGcoon..."
          disabled={loading}
          style={{
            flex: 1,
            padding: "12px 18px",
            borderRadius: "24px",
            border: "1px solid #cbd5e1",
            fontSize: "15px",
            outline: "none"
          }}
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          style={{
            padding: "12px 24px",
            borderRadius: "24px",
            border: "none",
            backgroundColor: loading || !input.trim() ? "#cbd5e1" : "#4f46e5",
            color: "#ffffff",
            fontWeight: "bold",
            cursor: loading || !input.trim() ? "not-allowed" : "pointer"
          }}
        >
          ส่งคำถาม
        </button>
      </form>
    </div>
  );
}