"use client";

export default function StoryCard({ what, soWhat, nowWhat, limitation }) {
  return (
    <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50/90 p-3.5 text-xs leading-relaxed text-slate-700 print-break-inside-avoid">
      <div className="grid gap-2 md:grid-cols-3">
        <div>
          <span className="inline-block rounded bg-blue-100 px-1.5 py-0.5 font-semibold text-blue-800">
            What (เกิดอะไรขึ้น)
          </span>
          <p className="mt-1">{what}</p>
        </div>
        <div>
          <span className="inline-block rounded bg-amber-100 px-1.5 py-0.5 font-semibold text-amber-800">
            So What (สำคัญอย่างไร)
          </span>
          <p className="mt-1">{soWhat}</p>
        </div>
        <div>
          <span className="inline-block rounded bg-emerald-100 px-1.5 py-0.5 font-semibold text-emerald-800">
            Now What (ควรทำอะไร)
          </span>
          <p className="mt-1">{nowWhat}</p>
        </div>
      </div>
      {limitation ? (
        <p className="mt-2 border-t border-slate-200 pt-1.5 text-[11px] text-slate-500">
          <strong>ข้อจำกัดข้อมูล:</strong> {limitation}
        </p>
      ) : null}
    </div>
  );
}
