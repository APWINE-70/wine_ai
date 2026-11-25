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
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-emerald-50 via-white to-teal-50 p-4">
      <div className="w-full max-w-md rounded-2xl border border-emerald-100 bg-white p-7 shadow-xl shadow-emerald-900/5">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-600 text-white shadow-sm shadow-emerald-600/20">
            <Zap className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-slate-900">Lanna Power Reliability</h1>
            <p className="text-xs text-emerald-700">Executive Outage Analytics (2566–2567)</p>
          </div>
        </div>

        <div className="mt-5 rounded-xl border border-emerald-200 bg-emerald-50/70 p-3.5 text-xs text-emerald-950">
          <div className="flex items-center gap-1.5 font-semibold text-emerald-800">
            <ShieldCheck className="h-4 w-4 text-emerald-600" />
            บัญชีทดสอบสำหรับคณะกรรมการ (Judge Test Account)
          </div>
          <p className="mt-1 font-mono text-[11px] text-emerald-900">
            Email: <strong>{DEMO_ACCOUNT.email}</strong> · Pass: <strong>{DEMO_ACCOUNT.password}</strong>
          </p>
        </div>

        <form onSubmit={handleSubmit} className="mt-4 space-y-3.5">
          <div>
            <label className="block text-xs font-medium text-slate-700">อีเมลผู้ใช้งาน</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-900 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
              required
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-700">รหัสผ่าน</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-900 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
              required
            />
          </div>
          {error ? <p className="text-xs font-medium text-rose-600">{error}</p> : null}
          <button
            type="submit"
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm shadow-emerald-600/20 transition hover:bg-emerald-700"
          >
            <Lock className="h-4 w-4" />
            เข้าสู่ระบบแดชบอร์ด
          </button>
        </form>
      </div>
    </div>
  );
}
