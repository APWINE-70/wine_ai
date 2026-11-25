"use client";

import { AlertTriangle, Database, Gauge, Loader2, ShieldAlert } from "lucide-react";

export default function AboutTab({
  perfStats,
  metadata,
  reliability,
  onSimulateLoading,
  onSimulateError,
}) {
  const raw23 = reliability.scenarios.raw_uncleaned_unplanned["2023"];
  const raw24 = reliability.scenarios.raw_uncleaned_unplanned["2024"];
  const cln23 = reliability.scenarios.clean_imputed_all_unplanned["2023"];
  const cln24 = reliability.scenarios.clean_imputed_all_unplanned["2024"];

  return (
    <div className="space-y-6">
      {/* Performance Benchmark (Mission F) */}
      <section className="rounded-2xl border border-emerald-100 bg-white p-5 shadow-sm shadow-emerald-950/[0.03]">
        <div className="flex items-center gap-2">
          <Gauge className="h-5 w-5 text-emerald-600" />
          <h2 className="text-sm font-bold text-slate-900">
            ผลการวัดประสิทธิภาพระบบ (Mission F: Performance Benchmark)
          </h2>
        </div>
        <div className="mt-4 grid gap-4 sm:grid-cols-3">
          <div className="rounded-xl border border-emerald-200 bg-emerald-50/70 p-4">
            <p className="text-xs font-medium text-emerald-800">First Load / App Hydration Time</p>
            <p className="mt-1 text-2xl font-bold text-emerald-950">
              {perfStats.firstLoadMs !== null ? `${perfStats.firstLoadMs.toFixed(1)} ms` : "กำลังวัด..."}
            </p>
            <p className="mt-1 text-[11px] text-emerald-800">
              ({perfStats.firstLoadMs !== null ? `${(perfStats.firstLoadMs / 1000).toFixed(3)} วินาที` : "-"} · เป้าหมาย &lt; 0.300 วินาที)
            </p>
          </div>
          <div className="rounded-xl border border-teal-200 bg-teal-50/70 p-4">
            <p className="text-xs font-medium text-teal-800">Filter Response Time (ล่าสุด / เฉลี่ย)</p>
            <p className="mt-1 text-2xl font-bold text-teal-950">
              {perfStats.lastFilterMs.toFixed(2)} ms
            </p>
            <p className="mt-1 text-[11px] text-teal-800">
              เฉลี่ยจากการกรอง {perfStats.filterCount} ครั้ง: {perfStats.avgFilterMs.toFixed(2)} ms
            </p>
          </div>
          <div className="rounded-xl border border-emerald-100 bg-white p-4">
            <p className="text-xs font-medium text-slate-600">ขอบเขตข้อมูล (Data Cutoff)</p>
            <p className="mt-1 text-lg font-bold text-slate-900">{metadata.data_cutoff}</p>
            <p className="mt-1 text-[11px] text-slate-600">
              ทะเบียนสายป้อน: {metadata.feeder_export_date} · Unplanned: {metadata.unplanned_events.toLocaleString()} ครั้ง
            </p>
          </div>
        </div>

        <div className="mt-4 rounded-xl bg-slate-50 p-4 text-xs leading-relaxed text-slate-700">
          <p className="font-semibold text-slate-900">เทคนิคการปรับแต่งความเร็วที่ใช้:</p>
          <ul className="mt-1.5 list-disc space-y-1 pl-5">
            <li>
              <strong>Python Pre-aggregation (`src/eda_analysis.py` &amp; `src/export_web_data.py`):</strong> คำนวณตารางสรุป, ค่าสถิติอากาศ, การจำลอง 3 โครงการ และบีบ schema เหตุการณ์เหลือเฉพาะคอลัมน์จำเป็นล่วงหน้า (ลดการ join ข้าม 4 ตารางในเบราว์เซอร์)
            </li>
            <li>
              <strong>Next.js Static Site Generation (`output: &quot;export&quot;`):</strong> คอมไพล์หน้าเว็บและข้อมูลเป็นไฟล์ Static HTML/JS พร้อมโหลดทันทีโดยไม่ต้องรอ Cold Start ของ Backend API หรือฐานข้อมูล
            </li>
            <li>
              <strong>Memoized Client Filtering (`React.useMemo`):</strong> การกรอง 5 มิติ (ปี × จังหวัด × สายป้อน × สาเหตุ × พื้นที่) + Toggle พายุ ประมวลผลในหน่วยความจำแบบ single-pass ใช้เวลา &lt; 10 ms
            </li>
          </ul>
        </div>
      </section>

      {/* Before vs After Cleaning Transparency */}
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex items-center gap-2">
          <Database className="h-5 w-5 text-emerald-600" />
          <h2 className="text-sm font-bold text-slate-900">
            ความโปร่งใสของข้อมูล: เปรียบเทียบก่อนคลีน vs หลังคลีน (Zero Silent Drops)
          </h2>
        </div>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full border-collapse text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-slate-600">
                <th className="px-3 py-2 font-semibold">ชุดข้อมูล</th>
                <th className="px-3 py-2 text-right font-semibold">2566 SAIFI</th>
                <th className="px-3 py-2 text-right font-semibold">2566 SAIDI (นาที)</th>
                <th className="px-3 py-2 text-right font-semibold">2567 SAIFI</th>
                <th className="px-3 py-2 text-right font-semibold">2567 SAIDI (นาที)</th>
                <th className="px-3 py-2 font-semibold">หมายเหตุ</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              <tr>
                <td className="px-3 py-2 font-medium text-rose-700">ข้อมูลดิบก่อนคลีน (Raw Unplanned)</td>
                <td className="px-3 py-2 text-right">{raw23.saifi.toFixed(2)}</td>
                <td className="px-3 py-2 text-right">{raw23.saidi.toFixed(1)}</td>
                <td className="px-3 py-2 text-right">{raw24.saifi.toFixed(2)}</td>
                <td className="px-3 py-2 text-right">{raw24.saidi.toFixed(1)}</td>
                <td className="px-3 py-2 text-slate-500">เพี้ยนจากค่า 99999 และลูกค้าเกินจริง</td>
              </tr>
              <tr>
                <td className="px-3 py-2 font-medium text-emerald-700">หลังคลีนครบ 14 รูปแบบ (Clean Imputed)</td>
                <td className="px-3 py-2 text-right">{cln23.saifi.toFixed(2)}</td>
                <td className="px-3 py-2 text-right">{cln23.saidi.toFixed(1)}</td>
                <td className="px-3 py-2 text-right">{cln24.saifi.toFixed(2)}</td>
                <td className="px-3 py-2 text-right">{cln24.saidi.toFixed(1)}</td>
                <td className="px-3 py-2 text-slate-500">Unplanned 2,594 ครั้ง (ตัด Planned 149 ครั้ง)</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      {/* State Verification Controls for Judges (Mission D) */}
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm no-print">
        <div className="flex items-center gap-2">
          <ShieldAlert className="h-5 w-5 text-amber-600" />
          <h2 className="text-sm font-bold text-slate-900">
            ทดสอบสถานะระบบสำหรับคณะกรรมการ (UI State Verification — ภารกิจ D)
          </h2>
        </div>
        <p className="mt-1 text-xs text-slate-500">
          ทดสอบหน้าจอแจ้งเตือนสถานะ Loading / Error พร้อมคำแนะนำแก้ไขได้ทันที (ส่วน Empty State ทดสอบได้โดยเลือกตัวกรองที่ไม่มีข้อมูลร่วมกัน)
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={onSimulateLoading}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
          >
            <Loader2 className="h-3.5 w-3.5" />
            ทดสอบสถานะ Loading
          </button>
          <button
            type="button"
            onClick={onSimulateError}
            className="inline-flex items-center gap-1.5 rounded-lg border border-rose-300 bg-rose-50 px-3 py-1.5 text-xs font-medium text-rose-800 hover:bg-rose-100"
          >
            <AlertTriangle className="h-3.5 w-3.5" />
            ทดสอบสถานะ Error พร้อมปุ่มกู้คืน
          </button>
        </div>
      </section>
    </div>
  );
}
