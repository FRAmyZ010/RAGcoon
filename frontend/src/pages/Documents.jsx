import { useState } from 'react';
import { 
  MoreVertical, Upload, FileText, ChevronDown, Search, 
  MessageCircle, Send, Bot, User, Sparkles, X 
} from 'lucide-react';
import Button from '../components/ui/Button';
import Table from '../components/ui/Table';
import FileActionMenu from '../components/ui/FileActionMenu';
import UploadModal from '../components/ui/UploadModal';

export default function Documents() {
  const [activeMenuIndex, setActiveMenuIndex] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [inputMessage, setInputMessage] = useState('');
  const [messages, setMessages] = useState([
    {
      id: 1,
      sender: 'ai',
      text: 'สวัสดีครับ! ผม RAGcoon AI มีเอกสารชุดไหนในคลังที่ต้องการให้ค้นหาหรือสรุปข้อมูลให้ไหมครับ?',
      sources: []
    }
  ]);

  const files = [
    { title: 'ProjectPetFeeder', year: '2022', category: 'IOT', status: 'Processing', date: '12 Jan 2025' },
    { title: 'ProjectWebapplication', year: '2023', category: 'Web Application', status: 'Ready', date: '12 Jan 2025' },
    { title: 'Networkmonitoring', year: '2023', category: 'Network', status: 'Processing', date: '12 Jan 2025' },
    { title: 'Preprojectnetwork', year: '2022', category: 'Network', status: 'Failed', date: '12 Jan 2025' },
    { title: 'ProjectFulldocument', year: '2021', category: 'IOT', status: 'Processing', date: '12 Jan 2025' },
    { title: 'Embeddedsystemproject', year: '2020', category: 'IOT', status: 'Processing', date: '12 Jan 2025' },
    { title: 'ProjectMachine', year: '2022', category: 'Machine Learning', status: 'Ready', date: '11 Jan 2025' },
  ];

  const filteredFiles = files.filter(f => 
    f.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const headers = ['Title', 'Year', 'Category', 'Status', 'Date', ''];

  const handleSendMessage = (e) => {
    e.preventDefault();
    if (!inputMessage.trim()) return;

    const userMsg = { id: Date.now(), sender: 'user', text: inputMessage };
    setMessages((prev) => [...prev, userMsg]);
    setInputMessage('');

    setTimeout(() => {
      const aiMsg = {
        id: Date.now() + 1,
        sender: 'ai',
        text: `สืบค้นข้อมูลเกี่ยวกับ "${inputMessage}" จากเอกสารในคลังเรียบร้อยแล้วครับ`,
        sources: [{ name: 'ProjectPetFeeder.pdf', page: 'หน้า 2' }]
      };
      setMessages((prev) => [...prev, aiMsg]);
    }, 800);
  };

  return (
    <div className="relative space-y-6 font-mono">
      <div className="flex justify-between items-center">
        <h2 className="text-xs text-gray-600 font-semibold">Desktop - doc management</h2>
        <div className="flex gap-2">
          <Button 
            variant="dark" 
            onClick={() => setIsChatOpen(!isChatOpen)}
          >
            <MessageCircle size={14} /> {isChatOpen ? 'Close AI Chat' : 'Open AI Chat'}
          </Button>
          <Button variant="primary" onClick={() => setIsModalOpen(true)}>
            <Upload size={14} /> Upload file
          </Button>
        </div>
      </div>

      <div className="flex gap-6">
        <div className="flex-1 space-y-6">
          <div className="space-y-2">
            <h3 className="text-xs font-bold text-gray-800">Recently modified</h3>
            <div className="grid grid-cols-3 gap-4">
              {[1, 2, 3].map((_, i) => (
                <div key={i} className="bg-white p-4 rounded-xl flex justify-between items-start shadow-sm border border-gray-100">
                  <div className="flex gap-3">
                    <FileText size={18} className="text-gray-700 mt-0.5" />
                    <div className="text-xs space-y-1">
                      <p className="font-bold text-gray-800">PROJECT-PetFeeder-Finalize</p>
                      <p className="text-[10px] text-gray-400">228 KB pdf</p>
                    </div>
                  </div>
                  <MoreVertical size={14} className="text-gray-400 cursor-pointer hover:text-black" />
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <div className="relative w-64">
                <Search size={14} className="absolute left-3 top-2.5 text-gray-400" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search documents..."
                  className="w-full bg-white text-xs pl-9 pr-4 py-1.5 rounded-lg border border-gray-200 focus:outline-none focus:border-gray-400"
                />
              </div>

              <div className="flex gap-2">
                {['Category', 'Modified', 'Years'].map((filter, i) => (
                  <button key={i} className="bg-gray-200 px-3 py-1.5 rounded text-[11px] font-semibold flex items-center gap-1 text-gray-700 hover:bg-gray-300">
                    {filter} <ChevronDown size={12} />
                  </button>
                ))}
              </div>
            </div>

            <h3 className="text-xs font-bold text-gray-800">All files</h3>

            <Table
              headers={headers}
              data={filteredFiles}
              renderRow={(file, idx) => (
                <tr key={idx} className="hover:bg-gray-50 border-b border-gray-100 relative">
                  <td className="p-4 flex items-center gap-2 font-bold text-gray-800 text-xs">
                    <FileText size={16} className="text-red-700" />
                    {file.title}
                  </td>
                  <td className="p-4 text-xs text-gray-600">{file.year}</td>
                  <td className="p-4 text-xs text-gray-600">{file.category}</td>
                  <td className="p-4 text-xs font-semibold text-gray-800">{file.status}</td>
                  <td className="p-4 text-xs text-gray-500">{file.date}</td>
                  <td className="p-4 text-right relative">
                    <MoreVertical
                      size={14}
                      className="cursor-pointer text-gray-400 hover:text-black inline"
                      onClick={() => setActiveMenuIndex(activeMenuIndex === idx ? null : idx)}
                    />
                    <FileActionMenu
                      isOpen={activeMenuIndex === idx}
                      onClose={() => setActiveMenuIndex(null)}
                    />
                  </td>
                </tr>
              )}
            />
          </div>
        </div>

        {isChatOpen && (
          <div className="w-80 bg-white rounded-xl border border-gray-200 shadow-xl flex flex-col h-[calc(100vh-10rem)] transition-all">
            <div className="p-3 border-b border-gray-100 flex justify-between items-center bg-gray-50 rounded-t-xl">
              <div className="flex items-center gap-2">
                <Sparkles size={14} className="text-blue-600" />
                <span className="text-xs font-bold text-gray-800">RAGcoon Assistant</span>
              </div>
              <button onClick={() => setIsChatOpen(false)} className="text-gray-400 hover:text-black">
                <X size={14} />
              </button>
            </div>

            <div className="flex-1 p-3 overflow-y-auto space-y-3">
              {messages.map((msg) => (
                <div key={msg.id} className={`flex gap-2 ${msg.sender === 'user' ? 'flex-row-reverse' : ''}`}>
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center text-white text-[10px] shrink-0 ${
                    msg.sender === 'user' ? 'bg-gray-800' : 'bg-[#2563EB]'
                  }`}>
                    {msg.sender === 'user' ? <User size={12} /> : <Bot size={12} />}
                  </div>
                  <div className="max-w-[85%] space-y-1">
                    <div className={`p-2.5 rounded-lg text-[11px] leading-relaxed ${
                      msg.sender === 'user' 
                        ? 'bg-[#2563EB] text-white rounded-tr-none' 
                        : 'bg-gray-100 text-gray-800 rounded-tl-none'
                    }`}>
                      {msg.text}
                    </div>
                    {msg.sources && msg.sources.length > 0 && (
                      <div className="text-[9px] text-blue-600 bg-blue-50 px-2 py-0.5 rounded font-semibold">
                        📍 {msg.sources[0].name}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>

            <form onSubmit={handleSendMessage} className="p-2 border-t border-gray-100 bg-gray-50 flex gap-1 rounded-b-xl">
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                placeholder="Ask AI..."
                className="flex-1 bg-white border border-gray-200 rounded-lg px-3 py-1.5 text-xs focus:outline-none focus:border-blue-500"
              />
              <button type="submit" className="bg-[#2563EB] text-white p-2 rounded-lg hover:bg-blue-700">
                <Send size={12} />
              </button>
            </form>
          </div>
        )}
      </div>

      <UploadModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} />
    </div>
  );
}