import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, Folder, MessageSquare, Sliders, LogOut } from 'lucide-react';

export default function Sidebar() {
  const location = useLocation();

  const menuItems = [
    { name: 'Dashboard', path: '/admin/dashboard', icon: LayoutDashboard },
    { name: 'Documents Management', path: '/admin/documents', icon: Folder },
    { name: 'Feedback', path: '/admin/feedback', icon: MessageSquare },
    { name: 'AI Configuration', path: '/admin/ai-config', icon: Sliders },
  ];

  return (
    <aside className="w-64 bg-[#2D2D2D] text-white flex flex-col justify-between p-4 m-4 rounded-xl h-[calc(100vh-2rem)] font-mono">
      <div>
        <div className="flex items-center gap-3 mb-8 px-2">
          <div className="w-8 h-8 bg-gray-400 rounded-full flex items-center justify-center text-xl">🦝</div>
          <h1 className="text-xl font-bold tracking-wide">RAGcoon</h1>
        </div>

        <nav className="space-y-2">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-4 py-2.5 rounded-lg text-xs font-semibold transition-colors ${
                  isActive ? 'bg-white text-black' : 'text-gray-300 hover:bg-[#3D3D3D]'
                }`}
              >
                <Icon size={16} />
                {item.name}
              </Link>
            );
          })}
        </nav>
      </div>

      <button className="flex items-center justify-between w-full px-4 py-2.5 bg-white text-black rounded-lg text-xs font-bold hover:bg-gray-100">
        <span>Log Out</span>
        <LogOut size={16} />
      </button>
    </aside>
  );
}