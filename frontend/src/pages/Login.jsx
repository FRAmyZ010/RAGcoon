import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { Eye, EyeOff } from "lucide-react";
import { isAuthenticated, login } from "../services/authApi";

export default function LoginPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  if (isAuthenticated()) {
    return <Navigate to="/documents" replace />;
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!username.trim()) {
      setError("Please enter your username");
      return;
    }
    if (!password.trim()) {
      setError("Please enter your password");
      return;
    }

    setError("");
    setIsLoading(true);
    try {
      await login(username.trim(), password);
      navigate("/documents", { replace: true });
    } catch (err) {
      setError(err.message || "Login failed");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen w-full select-none items-center justify-center bg-[#7a7a7a] p-4 sm:p-6 md:p-10">
      <div className="relative w-full max-w-[420px] rounded-3xl border border-white/5 bg-[#2b2b2b] px-6 pb-10 pt-12 shadow-2xl transition-all duration-300 sm:px-10">
        <div className="absolute -top-12 left-1/2 -translate-x-1/2">
          <div className="flex h-24 w-24 items-center justify-center rounded-full border border-white/10 bg-[#2b2b2b] p-1.5 shadow-xl sm:h-28 sm:w-28">
            <div className="flex h-full w-full items-center justify-center rounded-full border border-white/5 bg-[#3a3a3a] text-5xl sm:text-6xl">
              🦝
            </div>
          </div>
        </div>

        <div className="mb-8 mt-2 text-center">
          <h1 className="text-2xl font-extrabold tracking-wider text-white sm:text-3xl">
            RAGcoon
          </h1>
          <p className="mt-2 text-sm text-slate-400">Administrator sign in</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="mb-2 block text-center text-xs font-bold uppercase tracking-widest text-slate-300">
              Username
            </label>
            <input
              type="text"
              autoComplete="username"
              value={username}
              onChange={(e) => {
                setUsername(e.target.value);
                setError("");
              }}
              className="h-11 w-full rounded-md bg-white px-4 text-sm font-medium text-slate-900 transition focus:outline-none focus:ring-2 focus:ring-yellow-400 sm:h-12"
            />
          </div>

          <div>
            <label className="mb-2 block text-center text-xs font-bold uppercase tracking-widest text-slate-300">
              Password
            </label>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  setError("");
                }}
                className="h-11 w-full rounded-md bg-white py-0 pl-4 pr-12 text-sm font-medium text-slate-900 transition focus:outline-none focus:ring-2 focus:ring-yellow-400 sm:h-12"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-slate-500 hover:text-slate-800"
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          {error && (
            <div className="rounded-md border border-red-500/40 bg-red-500/20 p-3 text-center text-sm font-medium text-red-300">
              {error}
            </div>
          )}

          <div className="pt-2">
            <button
              type="submit"
              disabled={isLoading}
              className="flex h-12 w-full items-center justify-center gap-2 rounded-md bg-[#eed23e] text-sm font-bold uppercase tracking-wider text-slate-950 shadow-md transition hover:bg-[#e0c430] active:scale-[0.99] disabled:opacity-70"
            >
              {isLoading ? (
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-slate-950 border-t-transparent" />
              ) : (
                "Sign in"
              )}
            </button>
          </div>
        </form>

        <div className="mt-8 border-t border-white/10 pt-4 text-center">
          <Link
            to="/chat"
            className="text-sm text-slate-400 underline transition hover:text-yellow-400"
          >
            Back to Chat (no login)
          </Link>
        </div>
      </div>
    </div>
  );
}
