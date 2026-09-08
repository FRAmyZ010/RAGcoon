import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';

export default function MainLayout() {
  return (
    <div className="flex bg-[#D1D1D1] min-h-screen font-mono">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <header className="flex justify-between items-center py-4 px-8">
          <div></div>
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-full bg-red-800 text-white flex items-center justify-center text-xs font-bold">●</div>
            <span className="text-xs font-semibold text-gray-800">Marry Jann</span>
          </div>
        </header>

        <main className="flex-1 px-8 pb-8 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}