"use client";

export default function StoryCard({ what, soWhat, nowWhat, limitation }) {
  return (
    <div className="mt-4 rounded-xl border border-emerald-100 bg-emerald-50/40 p-3.5 text-xs leading-relaxed text-slate-700 print-break-inside-avoid">
      <div className="grid gap-2.5 md:grid-cols-3">
        <div>
          <span className="inline-block rounded-md bg-emerald-100 px-2 py-0.5 font-semibold text-emerald-800">
            What (เกิดอะไรขึ้น)
          </span>
          <p className="mt-1">{what}</p>
        </div>
        <div>
          <span className="inline-block rounded-md bg-amber-100 px-2 py-0.5 font-semibold text-amber-800">
            So What (สำคัญอย่างไร)
          </span>
          <p className="mt-1">{soWhat}</p>
        </div>
        <div>
          <span className="inline-block rounded-md bg-teal-100 px-2 py-0.5 font-semibold text-teal-800">
            Now What (ควรทำอะไร)
          </span>
          <p className="mt-1">{nowWhat}</p>
        </div>
      </div>
      {limitation ? (
        <p className="mt-2 border-t border-emerald-100 pt-1.5 text-[11px] text-slate-500">
          <strong>ข้อจำกัดข้อมูล:</strong> {limitation}
        </p>
      ) : null}
    </div>
  );
}
