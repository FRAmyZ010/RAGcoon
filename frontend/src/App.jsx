import React, { useState } from 'react';

export default function App() {
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // ฟังก์ชันสำหรับส่งคำถามไปยัง Backend
  const handleAskQuestion = async (e) => {
    if (e) e.preventDefault();
    if (!question.trim()) return;

    setLoading(true);
    setError('');
    setAnswer('');

    try {
      const response = await fetch('http://localhost:5000/api/ask-project', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ question }),
      });

      if (!response.ok) {
        throw new Error('เกิดข้อผิดพลาดในการดึงข้อมูลจาก Server');
      }

      const data = await response.json();
      setAnswer(data.answer);
    } catch (err) {
      setError(err.message || 'ไม่สามารถเชื่อมต่อกับ Server ได้');
    } finally {
      setLoading(false);
    }
  };

  // ดักจับการกด Enter เพื่อส่งข้อมูล (กด Shift + Enter เพื่อขึ้นบรรทัดใหม่)
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleAskQuestion();
    }
  };

  return (
    <div className="bg-slate-900 min-h-screen text-white flex flex-col items-center justify-center p-4">
      <div className="max-w-2xl w-full bg-slate-800 rounded-2xl p-6 shadow-2xl border border-slate-700">
        
        {/* หัวข้อโปรเจกต์ */}
        <h1 className="text-2xl md:text-3xl font-bold text-center mb-6 text-indigo-400">
          RAGcoon 🦝
        </h1>

        {/* ฟอร์มรับ Input คำถาม (ปรับเป็น textarea) */}
        <form onSubmit={handleAskQuestion} className="flex gap-2 mb-6 items-end">
          <textarea
            rows={1}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="พิมพ์คำถามเกี่ยวกับโปรเจกต์ที่นี่... (กด Shift + Enter เพื่อขึ้นบรรทัดใหม่)"
            className="flex-1 bg-slate-700 text-white placeholder-slate-400 px-4 py-3 rounded-xl border border-slate-600 focus:outline-none focus:border-indigo-500 transition resize-none break-words overflow-y-auto max-h-32"
          />
          <button
            type="submit"
            disabled={loading || !question.trim()}
            className="bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-600 text-white font-semibold px-6 py-3 rounded-xl transition duration-200 flex items-center justify-center min-w-[100px] h-[48px]"
          >
            {loading ? (
              <span className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></span>
            ) : (
              'ถาม'
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
              {/* เพิ่ม break-words และ whitespace-pre-wrap เพื่อตัดคำข้อความยาวๆ */}
              <p className="text-slate-200 leading-relaxed whitespace-pre-wrap break-words">
                {answer}
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