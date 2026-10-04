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
    <div className="relative flex min-h-screen w-full items-center justify-center bg-[#7a7a7a] px-4 py-12 sm:px-6">
      <div
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.14),transparent_46%),radial-gradient(circle_at_bottom,rgba(0,0,0,0.18),transparent_52%)]"
        aria-hidden
      />

      <div className="relative w-full max-w-[25.5rem] rounded-3xl border border-white/10 bg-[#2b2b2b] px-7 pb-7 pt-14 shadow-[0_18px_48px_rgba(0,0,0,0.32)] sm:px-9 sm:pb-8 sm:pt-16">
        <div className="absolute -top-11 left-1/2 -translate-x-1/2">
          <div className="flex h-[5.75rem] w-[5.75rem] items-center justify-center rounded-full border-2 border-[#eed23e]/45 bg-[#2b2b2b] p-1 shadow-[0_10px_24px_rgba(0,0,0,0.35)]">
            <div className="flex h-full w-full items-center justify-center overflow-hidden rounded-full bg-[#3a3a3a]">
              <span className="select-none text-[4.15rem] leading-none" aria-hidden>
                🦝
              </span>
            </div>
          </div>
        </div>

        <div className="mb-6 text-center">
          <h1 className="text-[1.7rem] font-bold tracking-wide text-white">RAGcoon</h1>
          <p className="mt-1.5 text-sm text-slate-400">Administrator sign in</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="login-username"
              className="mb-1.5 block text-center text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-300"
            >
              Username
            </label>
            <input
              id="login-username"
              type="text"
              autoComplete="username"
              value={username}
              onChange={(e) => {
                setUsername(e.target.value);
                setError("");
              }}
              className="h-11 w-full rounded-xl bg-white px-4 text-sm font-medium text-slate-900 shadow-sm outline-none transition focus:ring-2 focus:ring-[#eed23e]"
            />
          </div>

          <div>
            <label
              htmlFor="login-password"
              className="mb-1.5 block text-center text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-300"
            >
              Password
            </label>
            <div className="relative">
              <input
                id="login-password"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  setError("");
                }}
                className="h-11 w-full rounded-xl bg-white py-0 pl-4 pr-11 text-sm font-medium text-slate-900 shadow-sm outline-none transition focus:ring-2 focus:ring-[#eed23e]"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-1.5 top-1/2 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-lg text-slate-500 transition hover:bg-slate-100 hover:text-slate-800"
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          {error && (
            <div
              role="alert"
              className="rounded-xl border border-red-400/40 bg-red-500/15 px-3 py-2 text-center text-sm font-medium text-red-200"
            >
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-[#eed23e] text-sm font-bold uppercase tracking-[0.12em] text-slate-950 shadow-sm transition hover:bg-[#e0c430] active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-70"
          >
            {isLoading ? (
              <>
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-950 border-t-transparent" />
                Signing in
              </>
            ) : (
              "Sign in"
            )}
          </button>
        </form>

        <div className="mt-5 border-t border-white/10 pt-4 text-center">
          <Link
            to="/chat"
            className="text-sm text-slate-400 transition hover:text-[#eed23e]"
          >
            Back to Chat (no login)
          </Link>
        </div>
      </div>
    </div>
  );
}
