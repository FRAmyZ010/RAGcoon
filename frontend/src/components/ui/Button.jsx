const variants = {
  primary: 'bg-ember-600 text-white hover:bg-ember-700 disabled:bg-ember-100',
  secondary: 'bg-white text-ink-900 border border-line hover:bg-canvas',
  ghost: 'bg-transparent text-ink-900 hover:bg-canvas',
  danger: 'bg-white text-ember-700 border border-line hover:bg-ember-50',
};
const sizes = { sm: 'text-sm px-3 py-1.5', md: 'text-sm px-4 py-2' };

export default function Button({ children, variant = 'primary', size = 'md', icon: Icon, className = '', ...props }) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-lg font-medium
        transition-colors disabled:cursor-not-allowed disabled:opacity-60
        ${variants[variant]} ${sizes[size]} ${className}`}
      {...props}
    >
      {Icon && <Icon size={16} />}
      {children}
    </button>
  );
}