export default function Button({ children, variant = 'primary', className = '', ...props }) {
  const baseStyle = 'px-4 py-2 rounded-lg text-xs font-bold transition-colors flex items-center justify-center gap-2 font-mono';
  const variants = {
    primary: 'bg-[#2563EB] text-white hover:bg-blue-700',
    dark: 'bg-[#2D2D2D] text-white hover:bg-[#3D3D3D]',
    outline: 'border border-gray-300 text-gray-700 hover:bg-gray-100',
  };

  return (
    <button className={`${baseStyle} ${variants[variant]} ${className}`} {...props}>
      {children}
    </button>
  );
}