"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AlertCircle, CloudRain, Download, Printer, Truck } from "lucide-react";
import ChartWrapper from "./ChartWrapper";
import StoryCard from "./StoryCard";

export default function DrilldownTab({
  feederRows,
  agingAlerts,
  weatherAnalysis,
  restorationAnalysis,
  onSelectFeeder,
  onExportCsv,
  onPrintPdf,
}) {
  const top10 = feederRows.slice(0, 10);

  return (
    <div className="space-y-6">
      {/* Aging Equipment Callout */}
      {agingAlerts.map((al) => (
        <div
          key={al.feeder_id}
          className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-xs text-rose-950"
        >
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0 text-rose-600" />
            <span>
              <strong>สัญญาณเตือนอุปกรณ์เสื่อมสภาพ ({al.feeder_id}):</strong> สายป้อน {al.province} ({al.area_type},
              ติดตั้งปี {al.install_year}) ไม่ติด Top 5 customer-minutes แต่เหตุอุปกรณ์ชำรุดพุ่งจาก{" "}
              <strong>{al.equip_2023} → {al.equip_2024} ครั้ง (+280%)</strong>
            </span>
          </div>
          <button
            type="button"
            onClick={() => onSelectFeeder(al.feeder_id)}
            className="rounded-lg bg-rose-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-rose-700 no-print"
          >
            กรองดูสาย {al.feeder_id}
          </button>
        </div>
      ))}

      {/* Top 10 Feeders */}
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm print-break-inside-avoid">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-sm font-bold text-slate-900">
              Top 10 สายป้อนที่สร้างผลกระทบสูงสุด (Customer-Minutes)
            </h2>
            <p className="text-xs text-slate-500">
              คลิกแท่งกราฟหรือรหัสสายป้อนในตารางเพื่อเจาะลึกข้อมูลเฉพาะสายป้อนนั้น
            </p>
          </div>
          <div className="flex items-center gap-2 no-print">
            <button
              type="button"
              onClick={onExportCsv}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
            >
              <Download className="h-3.5 w-3.5" />
              Export CSV
            </button>
            <button
              type="button"
              onClick={onPrintPdf}
              className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-800"
            >
              <Printer className="h-3.5 w-3.5" />
              Export PDF
            </button>
          </div>
        </div>

        <div className="mt-3">
          <ChartWrapper height={290}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={top10}
                layout="vertical"
                margin={{ top: 5, right: 24, left: 10, bottom: 5 }}
                onClick={(state) => {
                  if (state && state.activeLabel) {
                    onSelectFeeder(state.activeLabel);
                  }
                }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis type="number" tick={{ fontSize: 11 }} unit="M" />
                <YAxis type="category" dataKey="feeder_id" width={72} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="cmMillion" name="Customer-Minutes (ล้าน)" fill="#0284c7" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartWrapper>
        </div>

        <StoryCard
          what="Top 5 สายป้อน (CRI-F11, CRI-F03, CRI-F04, LPG-F09, CRI-F13) รวมกันสร้างความเสียหาย 32.51% ของทั้งระบบ ทั้งหมดเป็นสายชนบท สายอากาศ 100% ยาว 70–85 กม. และ Tree Cover สูง"
          soWhat="งบปรับปรุงที่กระจายเฉลี่ยเท่ากันทุกสายป้อน 54 สายจะได้ผลต่ำกว่าการโฟกัส 5 สายวิกฤตนี้ซึ่งมีอัตราไฟดับจากต้นไม้สูงถึง 41.55 ครั้ง/100 กม./ปี (9.1 เท่าของสาย low)"
          nowWhat="จัดลำดับงบเฟสแรกให้ Top 5 สายป้อนนี้ทันที พร้อมจัดสรรงบเปลี่ยนอุปกรณ์เร่งด่วนให้ CMI-F14 คู่ขนานกัน"
          limitation="มีเหตุการณ์ Unplanned 10 แถว (0.36%) ที่รหัสสายป้อนกำพร้า (orphan) จึงไม่ปรากฏในตารางจัดอันดับรายสายป้อน"
        />
      </section>

      {/* Weather + Restoration */}
      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm print-break-inside-avoid">
          <div className="flex items-center gap-2">
            <CloudRain className="h-4 w-4 text-sky-600" />
            <h2 className="text-sm font-bold text-slate-900">
              สภาพอากาศ vs อัตราไฟดับเฉลี่ยต่อจังหวัด/วัน
            </h2>
          </div>
          <p className="mt-0.5 text-xs text-slate-500">
            วันมีพายุฟ้าคะนองเสี่ยงสูงขึ้น <strong>{weatherAnalysis.thunderstorm_comparison.thunderstorm_risk_multiplier} เท่า</strong>{" "}
            (1.73 vs 0.74 ครั้ง/วัน) · Pearson r(ฝน) = {weatherAnalysis.correlations_daily_province.rainfall_mm_pearson}
          </p>
          <div className="mt-3">
            <ChartWrapper height={240}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={weatherAnalysis.by_rain_tier} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="rain_tier" tick={{ fontSize: 10 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="avg_outages_per_day" name="ไฟดับเฉลี่ย (ครั้ง/จังหวัด/วัน)" fill="#0ea5e9" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartWrapper>
          </div>
          <StoryCard
            what="วันที่ฝนตกหนัก (>35 มม.) เกิดไฟดับเฉลี่ย 2.25 ครั้ง/วัน เทียบ 0.70 ครั้ง/วันในวันที่ไม่มีฝน (3.2 เท่า) และวันลมแรง >45 กม./ชม. พุ่งถึง 2.82 ครั้ง/วัน"
            soWhat="พยากรณ์อากาศที่มีพายุฟ้าคะนองและลมแรงเป็นสัญญาณเตือนล่วงหน้าที่ใช้เตรียมกำลังคนได้แม่นยำกว่าอุณหภูมิ (r=0.09)"
            nowWhat="เชื่อมต่อการแจ้งเตือนพายุรายวันของกรมอุตุฯ เข้ากับระบบเตรียมทีมช่างล่วงหน้าเมื่อคาดการณ์ฝน >35 มม. หรือลม >45 กม./ชม."
            limitation="ข้อมูลอากาศเป็นค่ารายวันระดับจังหวัด ขาดหาย 25 province-days และเดิมมีค่าฝน -999 (40 วัน) ที่ต้องแปลงเป็น NaN"
          />
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm print-break-inside-avoid">
          <div className="flex items-center gap-2">
            <Truck className="h-4 w-4 text-amber-600" />
            <h2 className="text-sm font-bold text-slate-900">
              เวลากู้คืนและเวลาเดินทางช่างตามพื้นที่ (Urban / Suburban / Rural)
            </h2>
          </div>
          <p className="mt-0.5 text-xs text-slate-500">
            เวลาเดินทางช่างคิดเป็น 34.7%–39.1% (มัธยฐาน) ของระยะเวลาดับทั้งหมด · r = {restorationAnalysis.crew_vs_duration_pearson}
          </p>
          <div className="mt-3">
            <ChartWrapper height={240}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={restorationAnalysis.by_area_type} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="area_type" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} unit=" น." />
                  <Tooltip />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Bar dataKey="duration_median_min" name="มัธยฐานเวลาดับ (นาที)" fill="#f97316" radius={[6, 6, 0, 0]} />
                  <Bar dataKey="crew_arrival_median_min" name="มัธยฐานเวลาเดินทางช่าง (นาที)" fill="#334155" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartWrapper>
          </div>
          <StoryCard
            what="เขตชนบทใช้เวลากู้ไฟมัธยฐาน 122.0 นาที นานกว่าเขตเมือง (43.5 นาที) ถึง 2.8 เท่า โดยเวลาเดินทางช่างในชนบทอยู่ที่ 49.0 นาที เทียบกับเมือง 18.0 นาที"
            soWhat="เวลาเดินทางที่ยาวนานในสายชนบทยาวกว่า 70 กม. ทำให้ระยะเวลารอคอยของลูกค้าและ CAIDI พุ่งสูง (187.0 นาที ในชนบท vs 70.7 นาที ในเมือง)"
            nowWhat="ตั้งจุดเตรียมทีมช่างส่วนหน้า (Forward Dispatch) ในพื้นที่ชนบทเชียงรายและเพิ่มอุปกรณ์ตัดตอนอัตโนมัติ (Recloser)"
            limitation="ขาดข้อมูล crew_arrival_min 135 แถว (รวม 8 แถวติดลบที่ล้างออก) และมี 405 แถวที่ระบบกู้คืนอัตโนมัติก่อนช่างถึงหน้างาน"
          />
        </section>
      </div>

      {/* Feeder Detail Table */}
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-bold text-slate-900">
          ตารางรายละเอียดรายสายป้อนตามตัวกรองปัจจุบัน ({feederRows.length} สายป้อน)
        </h2>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full border-collapse text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-slate-600">
                <th className="px-3 py-2 font-semibold">Feeder</th>
                <th className="px-3 py-2 font-semibold">จังหวัด</th>
                <th className="px-3 py-2 font-semibold">พื้นที่</th>
                <th className="px-3 py-2 text-right font-semibold">ยาว (กม.)</th>
                <th className="px-3 py-2 font-semibold">Tree Cover</th>
                <th className="px-3 py-2 text-right font-semibold">ครั้ง (2566→2567)</th>
                <th className="px-3 py-2 text-right font-semibold">อัตรา/100กม./ปี</th>
                <th className="px-3 py-2 text-right font-semibold">มัธยฐาน (นาที)</th>
                <th className="px-3 py-2 text-right font-semibold">Customer-Min (ล้าน)</th>
                <th className="px-3 py-2 text-right font-semibold">% ผลกระทบ</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {feederRows.map((row) => (
                <tr
                  key={row.feeder_id}
                  onClick={() => onSelectFeeder(row.feeder_id)}
                  className="cursor-pointer hover:bg-sky-50/70"
                >
                  <td className="px-3 py-2 font-semibold text-sky-700">{row.feeder_id}</td>
                  <td className="px-3 py-2">{row.province}</td>
                  <td className="px-3 py-2">{row.area_type}</td>
                  <td className="px-3 py-2 text-right">{row.length_km}</td>
                  <td className="px-3 py-2">
                    <span
                      className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${
                        row.tree_cover === "high"
                          ? "bg-rose-100 text-rose-800"
                          : row.tree_cover === "medium"
                          ? "bg-amber-100 text-amber-800"
                          : "bg-emerald-100 text-emerald-800"
                      }`}
                    >
                      {row.tree_cover}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right">
                    {row.count} <span className="text-[10px] text-slate-400">({row.count2023}→{row.count2024})</span>
                  </td>
                  <td className="px-3 py-2 text-right">{row.ratePer100KmYr}</td>
                  <td className="px-3 py-2 text-right">{row.medianDur}</td>
                  <td className="px-3 py-2 text-right font-medium">{row.cmMillion.toFixed(2)}</td>
                  <td className="px-3 py-2 text-right font-semibold">{row.cmSharePct.toFixed(2)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
