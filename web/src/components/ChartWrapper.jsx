"use client";

import { useEffect, useState } from "react";

/**
 * Client-only mount guard for Recharts to prevent Next.js SSR/SSG hydration mismatch (React Error #423).
 */
export default function ChartWrapper({ height = 300, children }) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <div
        className="w-full animate-pulse rounded-lg bg-slate-100"
        style={{ height }}
        aria-label="กำลังโหลดกราฟ"
      />
    );
  }

  return <div style={{ width: "100%", height }}>{children}</div>;
}
