"use client";

import { useState } from "react";
import { Lock, ShieldCheck, Zap } from "lucide-react";

export const DEMO_ACCOUNT = {
  email: "judge@lannapower.co.th",
  password: "Lanna2025!",
};

export default function LoginGate({ onAuthenticated }) {
  const [email, setEmail] = useState(DEMO_ACCOUNT.email);
  const [password, setPassword] = useState(DEMO_ACCOUNT.password);
  const [error, setError] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (email.trim() === DEMO_ACCOUNT.email && password === DEMO_ACCOUNT.password) {
      setError("");
      onAuthenticated();
    } else {
      setError("อีเมลหรือรหัสผ่านไม่ถูกต้อง กรุณาใช้บัญชีทดสอบของคณะกรรมการด้านล่าง");
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-sky-950 p-4">
      <div className="w-full max-w-md rounded-2xl border border-slate-700/60 bg-white p-6 shadow-2xl">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-sky-600 text-white">
            <Zap className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-slate-900">Lanna Power Reliability</h1>
            <p className="text-xs text-slate-500">Executive Outage Analytics (2566–2567)</p>
          </div>
        </div>

        <div className="mt-4 rounded-xl border border-sky-200 bg-sky-50 p-3 text-xs text-sky-900">
          <div className="flex items-center gap-1.5 font-semibold">
            <ShieldCheck className="h-4 w-4 text-sky-700" />
            บัญชีทดสอบสำหรับคณะกรรมการ (Judge Test Account)
          </div>
          <p className="mt-1 font-mono text-[11px]">
            Email: <strong>{DEMO_ACCOUNT.email}</strong> · Pass: <strong>{DEMO_ACCOUNT.password}</strong>
          </p>
        </div>

        <form onSubmit={handleSubmit} className="mt-4 space-y-3">
          <div>
            <label className="block text-xs font-medium text-slate-700">อีเมลผู้ใช้งาน</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none"
              required
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-700">รหัสผ่าน</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none"
              required
            />
          </div>
          {error ? <p className="text-xs font-medium text-rose-600">{error}</p> : null}
          <button
            type="submit"
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-sky-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-sky-700"
          >
            <Lock className="h-4 w-4" />
            เข้าสู่ระบบแดชบอร์ด
          </button>
        </form>
      </div>
    </div>
  );
}
