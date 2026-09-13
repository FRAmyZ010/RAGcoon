import React, { useState } from "react";
import './App.css'

export default function App() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [source, setSource] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // ฟังก์ชันสำหรับส่งคำถามไปยัง Backend
  const handleAskQuestion = async (e) => {
    e.preventDefault();
    if (!question.trim()) return;

    setLoading(true);
    setError("");
    setAnswer("");

    try {
      // เปลี่ยน URL นี้ให้ตรงกับ Backend API ของคุณ
      const response = await fetch("http://localhost:8000/api/v1/chat/query", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query_text: question, // แก้จาก question เป็น query_text ให้ตรงกับ FastAPI Schema
        }),
      });

      if (!response.ok) {
        throw new Error("เกิดข้อผิดพลาดในการดึงข้อมูลจาก Server");
      }

      const data = await response.json();
      // สมมติว่า Backend ตอบกลับมาในรูปแบบ { answer: "คำตอบ..." }
      setAnswer(data.answer);
      setSource(data.sources);
    } catch (err) {
      setError(err.message || "ไม่สามารถเชื่อมต่อกับ Server ได้");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-slate-900 min-h-screen text-white flex flex-col items-center justify-center p-4">
      <div className="max-w-2xl w-full bg-slate-800 rounded-2xl p-6 shadow-2xl border border-slate-700">
        {/* หัวข้อโปรเจกต์ */}
        <h1 className="text-2xl md:text-3xl font-bold text-center mb-6 text-indigo-400">
          🦝 RAGcoon 🦝
        </h1>

        {/* ฟอร์มรับ Input คำถาม */}
        <form onSubmit={handleAskQuestion} className="flex gap-2 mb-6">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="พิมพ์คำถามเกี่ยวกับโปรเจกต์ที่นี่..."
            className="input-box flex-1 bg-slate-700 text-white placeholder-slate-400 px-4 py-3 rounded-xl border border-slate-600 focus:outline-none focus:border-indigo-500 transition"
          />
          <button
            type="submit"
            disabled={loading || !question.trim()}
            className="bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-600 text-white font-semibold px-6 py-3 rounded-xl transition duration-200 flex items-center justify-center min-w-[100px]"
          >
            {loading ? (
              <span className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></span>
            ) : (
              "ถาม"
            )}
          </button>
        </form>

        {/* ส่วนแสดงผลคำตอบจาก Backend */}
        <div className="bg-slate-900 rounded-xl p-5 border border-slate-700 min-h-[150px] flex flex-col justify-center">
          {loading && (
            <p className="text-slate-400 text-center animate-pulse">
              กำลังค้นหาข้อมูลโปรเจกต์และประมวลผลคำตอบ...
            </p>
          )}

          {error && (
            <div className="text-red-400 text-center font-medium">
              ❌ {error}
            </div>
          )}

          {!loading && !error && answer && (
            <div>
              <h2 className="text-sm font-semibold text-indigo-400 uppercase tracking-wider mb-2">
                คำตอบ:
              </h2>
              <p className="text-slate-200 leading-relaxed whitespace-pre-line">
                {answer}
              </p>
              <h2 className="text-sm font-semibold text-indigo-400 uppercase tracking-wider mb-2">
                แหล่งอ้างอิง:
              </h2>

              <p className="text-slate-200 leading-relaxed">
                {Array.isArray(source) && source.length > 0
                  ? source.join(", ")
                  : "ไม่พบข้อมูลแหล่งอ้างอิง"}
              </p>
            </div>
          )}

          {!loading && !error && !answer && (
            <p className="text-slate-500 text-center">
              ยังไม่มีคำถาม กรุณาพิมพ์คำถามในช่องด้านบน
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
