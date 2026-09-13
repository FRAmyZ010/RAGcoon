import { Download, Copy, Edit3, Trash2 } from 'lucide-react';

export default function FileActionMenu({ isOpen, onClose }) {
  if (!isOpen) return null;

  const actions = [
    { label: 'Download', icon: Download },
    { label: 'Copy', icon: Copy },
    { label: 'Rename', icon: Edit3 },
    { label: 'Remove', icon: Trash2 },
  ];

  return (
    <>
      <div className="fixed inset-0 z-10" onClick={onClose} />
      <div className="absolute right-6 top-10 w-40 bg-gray-200 shadow-xl rounded-lg py-1 z-20 text-xs font-mono border border-gray-300">
        {actions.map((act, i) => {
          const Icon = act.icon;
          return (
            <button
              key={i}
              onClick={onClose}
              className="w-full px-3 py-2 flex items-center gap-2 text-gray-800 hover:bg-gray-300 font-semibold"
            >
              <Icon size={14} />
              {act.label}
            </button>
          );
        })}
      </div>
    </>
  );
}