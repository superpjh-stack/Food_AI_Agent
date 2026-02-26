"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/lib/auth";
import { Shield, Leaf, ChefHat, ClipboardCheck } from "lucide-react";

const QUICK_LOGINS = [
  {
    role: "ADM",
    label: "관리자",
    username: "admin",
    email: "admin@smallsf.com",
    password: "admin1234",
    icon: Shield,
    color: "text-purple-600 bg-purple-50 hover:bg-purple-100 border-purple-200",
  },
  {
    role: "NUT",
    label: "영양사",
    username: "nutritionist",
    email: "nutritionist@smallsf.com",
    password: "nut1234",
    icon: Leaf,
    color: "text-green-600 bg-green-50 hover:bg-green-100 border-green-200",
  },
  {
    role: "KIT",
    label: "조리사",
    username: "kitchen",
    email: "kitchen@smallsf.com",
    password: "kit1234",
    icon: ChefHat,
    color: "text-orange-600 bg-orange-50 hover:bg-orange-100 border-orange-200",
  },
  {
    role: "QLT",
    label: "위생관리",
    username: "quality",
    email: "quality@smallsf.com",
    password: "qlt1234",
    icon: ClipboardCheck,
    color: "text-blue-600 bg-blue-50 hover:bg-blue-100 border-blue-200",
  },
];

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeQuick, setActiveQuick] = useState<string | null>(null);

  // username → email 변환 (@ 없으면 @smallsf.com 붙임)
  const resolveEmail = (input: string) =>
    input.includes("@") ? input : `${input}@smallsf.com`;

  const doLogin = async (e: string, p: string, role?: string) => {
    setLoading(true);
    setError("");
    if (role) setActiveQuick(role);
    try {
      await login(resolveEmail(e), p);
      router.push("/dashboard");
    } catch {
      setError("아이디 또는 비밀번호가 올바르지 않습니다.");
    } finally {
      setLoading(false);
      setActiveQuick(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await doLogin(email, password);
  };

  const handleQuickLogin = (q: (typeof QUICK_LOGINS)[0]) => {
    setEmail(q.username);
    setPassword(q.password);
    doLogin(q.username, q.password, q.role);
  };

  return (
    <div className="w-full max-w-md rounded-lg border bg-card p-8 shadow-sm">
      <div className="mb-6 text-center">
        <h1 className="text-2xl font-bold text-foreground">Food AI Agent</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Sign in to your account
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
            {error}
          </div>
        )}

        <div>
          <label htmlFor="email" className="block text-sm font-medium">
            아이디 / 이메일
          </label>
          <input
            id="email"
            type="text"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 block w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary"
            placeholder="admin"
          />
        </div>

        <div>
          <label htmlFor="password" className="block text-sm font-medium">
            Password
          </label>
          <input
            id="password"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 block w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {loading && !activeQuick ? "Signing in..." : "Sign in"}
        </button>
      </form>

      {/* Quick Login */}
      <div className="mt-6">
        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-border" />
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-card px-2 text-muted-foreground">
              개발 퀵로그인
            </span>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-4 gap-2">
          {QUICK_LOGINS.map((q) => {
            const Icon = q.icon;
            const isActive = activeQuick === q.role;
            return (
              <button
                key={q.role}
                type="button"
                disabled={loading}
                onClick={() => handleQuickLogin(q)}
                className={`flex flex-col items-center gap-1.5 rounded-lg border px-2 py-3 text-xs font-medium transition-all disabled:opacity-50 ${q.color}`}
                title={`${q.label}: ${q.username} / ${q.password}`}
              >
                {isActive ? (
                  <svg
                    className="h-5 w-5 animate-spin"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8v8H4z"
                    />
                  </svg>
                ) : (
                  <Icon className="h-5 w-5" />
                )}
                <span>{q.label}</span>
                <span className="text-[10px] opacity-60">{q.role}</span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
