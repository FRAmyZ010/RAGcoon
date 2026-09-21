import React, { useState } from "react";
import { Link } from "react-router-dom";
import { FolderText, Send, Bot, User, Menu, X } from "lucide-react";

export default function Chat() {
  const [messages, setMessages] = useState([
    { id: 1, sender: "bot", text: "สวัสดีครับ มีคำถามเกี่ยวกับเอกสารโครงงานชิ้นไหน สอบถามได้เลยครับ" }
  ]);
  const [inputQuery, setInputQuery] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!inputQuery.trim()) return;

    const userMessage = { id: Date.now(), sender: "user", text: inputQuery };
    setMessages((prev) => [...prev, userMessage]);
    setInputQuery("");
  };

  return (
    <div className="flex h-screen bg-gray-50 font-mono text-[#353535] overflow-hidden">
      
      {/* 🔴 Responsive Sidebar Drawer (ซ่อนแบบ Overlay บนมือถือ / โชว์ปกติบนจอใหญ่ lg:) */}
      <div 
        className={`fixed inset-y-0 left-0 z-40 w-64 bg-white border-r border-gray-200 transform transition-transform duration-200 ease-in-out lg:static lg:translate-x-0 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex flex-col h-full p-4">
          <div className="flex justify-between items-center mb-6">
            <h2 className="font-bold text-sm text-gray-700">Chat Workspaces</h2>
            <button onClick={() => setSidebarOpen(false)} className="lg:hidden p-1 text-gray-500">
              <X className="h-5 w-5" />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto space-y-2">
            <div className="p-2.5 bg-blue-50 text-[#1D61E7] rounded-lg text-xs font-bold truncate cursor-pointer">
              💬 โครงงานระบบอัตโนมัติ 2024
            </div>
          </div>
        </div>
      </div>

      {/* Main Area */}
      <div className="flex-1 flex flex-col h-full min-w-0">
        
        {/* 🔴 Top Header Bar */}
        <div className="bg-white border-b border-gray-200 p-3 sm:p-4 flex justify-between items-center shrink-0">
          <div className="flex items-center gap-2">
            {/* ปุ่มเปิด Sidebar บนมือถือ */}
            <button 
              onClick={() => setSidebarOpen(true)} 
              className="p-1.5 text-gray-600 lg:hidden hover:bg-gray-100 rounded-lg"
            >
              <Menu className="h-5 w-5" />
            </button>
            <h1 className="font-bold text-xs sm:text-sm text-gray-800 truncate">RAGcoon Query Assistant</h1>
          </div>

          {/* 🔵 ปุ่มลิงก์สลับไปหน้า Documents ( Responsive: ซ่อนคำว่า Documents บนมือถือ ) */}
          <Link
            to="/documents"
            className="px-3 py-1.5 sm:px-4 sm:py-2 bg-white border border-gray-300 hover:bg-gray-100 text-gray-700 rounded-lg shadow-sm flex items-center gap-2 transition text-xs font-bold"
            title="ไปที่หน้า Documents"
          >
            <FolderText className="h-4 w-4 text-[#800000]" />
            <span className="hidden sm:inline">Documents</span>
          </Link>
        </div>

        {/* Chat Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex items-start gap-2.5 max-w-[85%] sm:max-w-[75%] ${
                msg.sender === "user" ? "ml-auto flex-row-reverse" : "mr-auto"
              }`}
            >
              <div className={`p-2 rounded-lg shrink-0 ${msg.sender === "user" ? "bg-blue-600 text-white" : "bg-red-800 text-white"}`}>
                {msg.sender === "user" ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
              </div>
              <div className={`p-3 rounded-xl text-xs sm:text-sm leading-relaxed ${
                msg.sender === "user" ? "bg-[#1D61E7] text-white rounded-tr-none" : "bg-white border text-gray-800 rounded-tl-none shadow-sm"
              }`}>
                {msg.text}
              </div>
            </div>
          ))}
        </div>

        {/* Input Bar */}
        <div className="p-3 sm:p-4 bg-white border-t border-gray-200 shrink-0">
          <form onSubmit={handleSend} className="flex items-center gap-2 max-w-4xl mx-auto">
            <input
              type="text"
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              placeholder="พิมพ์คำถามเกี่ยวกับโครงงานที่นี่..."
              className="flex-1 p-2.5 sm:p-3 border border-gray-300 rounded-xl text-xs sm:text-sm focus:outline-none focus:border-[#1D61E7]"
            />
            <button type="submit" className="p-2.5 sm:p-3 bg-[#1D61E7] hover:bg-blue-700 text-white rounded-xl transition shrink-0">
              <Send className="h-4 w-4" />
            </button>
          </form>
        </div>

      </div>
    </div>
  );
}