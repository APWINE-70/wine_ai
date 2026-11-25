"use client";

const DAY_LABELS = ["จันทร์", "อังคาร", "พุธ", "พฤหัสฯ", "ศุกร์", "เสาร์", "อาทิตย์"];
const HOURS = Array.from({ length: 24 }, (_, idx) => idx);

export default function Heatmap24x7({ cells, maxCount }) {
  const lookup = new Map();
  for (const c of cells) {
    lookup.set(`${c.dow}-${c.hour}`, c);
  }

  const getBg = (count) => {
    if (!count || maxCount <= 0) return "bg-slate-100 text-slate-400";
    const ratio = count / maxCount;
    if (ratio >= 0.75) return "bg-rose-700 text-white font-semibold";
    if (ratio >= 0.5) return "bg-orange-500 text-white font-medium";
    if (ratio >= 0.3) return "bg-amber-300 text-slate-900";
    if (ratio >= 0.15) return "bg-amber-100 text-slate-800";
    return "bg-sky-50 text-slate-700";
  };

  return (
    <div className="overflow-x-auto">
      <div className="min-w-[680px]">
        <div className="mb-1 grid grid-cols-[64px_repeat(24,minmax(22px,1fr))] gap-1 text-center text-[10px] text-slate-500">
          <div />
          {HOURS.map((h) => (
            <div key={h}>{String(h).padStart(2, "0")}</div>
          ))}
        </div>
        <div className="space-y-1">
          {DAY_LABELS.map((dayName, dow) => (
            <div
              key={dayName}
              className="grid grid-cols-[64px_repeat(24,minmax(22px,1fr))] items-center gap-1"
            >
              <div className="pr-2 text-right text-xs font-medium text-slate-600">{dayName}</div>
              {HOURS.map((hour) => {
                const cell = lookup.get(`${dow}-${hour}`);
                const cnt = cell ? cell.count : 0;
                const cm = cell ? cell.cm : 0;
                return (
                  <div
                    key={hour}
                    title={`${dayName} ${String(hour).padStart(2, "0")}:00 น. — ${cnt} ครั้ง (${Math.round(cm).toLocaleString()} customer-min)`}
                    className={`flex h-7 items-center justify-center rounded text-[10px] transition ${getBg(cnt)}`}
                  >
                    {cnt > 0 ? cnt : ""}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
        <div className="mt-2 flex flex-wrap items-center justify-end gap-3 text-[11px] text-slate-500">
          <span>ความถี่:</span>
          <span className="inline-flex items-center gap-1"><span className="h-3 w-3 rounded bg-slate-100 border border-slate-200" /> 0</span>
          <span className="inline-flex items-center gap-1"><span className="h-3 w-3 rounded bg-amber-100" /> ต่ำ</span>
          <span className="inline-flex items-center gap-1"><span className="h-3 w-3 rounded bg-amber-300" /> ปานกลาง</span>
          <span className="inline-flex items-center gap-1"><span className="h-3 w-3 rounded bg-orange-500" /> สูง</span>
          <span className="inline-flex items-center gap-1"><span className="h-3 w-3 rounded bg-rose-700" /> พีกสุด</span>
        </div>
      </div>
    </div>
  );
}
