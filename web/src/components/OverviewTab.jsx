"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Activity, AlertTriangle, Clock, CloudLightning, Users, Zap } from "lucide-react";
import ChartWrapper from "./ChartWrapper";
import Heatmap24x7 from "./Heatmap24x7";
import StoryCard from "./StoryCard";

function KpiCard({ title, value, unit, subtext, icon: Icon, tone = "sky" }) {
  const tones = {
    sky: "bg-sky-50 text-sky-700",
    rose: "bg-rose-50 text-rose-700",
    amber: "bg-amber-50 text-amber-700",
    emerald: "bg-emerald-50 text-emerald-700",
    indigo: "bg-indigo-50 text-indigo-700",
  };
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-slate-500">{title}</p>
          <p className="mt-1 text-2xl font-bold tracking-tight text-slate-900">
            {value} <span className="text-xs font-normal text-slate-500">{unit}</span>
          </p>
        </div>
        <div className={`rounded-lg p-2 ${tones[tone] || tones.sky}`}>
          <Icon className="h-4 w-4" />
        </div>
      </div>
      {subtext ? <p className="mt-2 text-[11px] text-slate-600">{subtext}</p> : null}
    </div>
  );
}

export default function OverviewTab({
  kpis,
  yoySeries,
  pareto,
  monthly,
  heatmap,
  includeStorm,
  stormRecon,
  yearFilter,
}) {
  const y23 = yoySeries.find((r) => r.year === "2566 (2023)");
  const y24 = yoySeries.find((r) => r.year === "2567 (2024)");
  const saidiPct =
    y23 && y24 && y23.saidi > 0
      ? (((y24.saidi - y23.saidi) / y23.saidi) * 100).toFixed(1)
      : null;

  return (
    <div className="space-y-6">
      {!includeStorm ? (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-xs text-amber-950">
          <div className="flex items-center gap-2">
            <CloudLightning className="h-4 w-4 shrink-0 text-amber-700" />
            <span>
              <strong>โหมดไม่รวมพายุใหญ่เชียงราย (22–23 ส.ค. 2567):</strong> แยกเหตุการณ์พายุ{" "}
              <strong>{stormRecon.storm_event_count} ครั้ง</strong> ({stormRecon.share_of_2024_customer_minutes_pct}%
              ของ customer-minutes ปี 2567 หรือ {stormRecon.saidi_contribution_2024_min.toFixed(2)} นาทีของ SAIDI) ออกเพื่อดูแนวโน้มปกติ
            </span>
          </div>
        </div>
      ) : null}

      {/* KPI Cards */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <KpiCard
          title="เหตุการณ์ไฟดับ (Unplanned)"
          value={kpis.count.toLocaleString()}
          unit="ครั้ง"
          subtext={yearFilter === "ALL" && y23 && y24 ? `2566: ${y23.count.toLocaleString()} → 2567: ${y24.count.toLocaleString()}` : "เฉพาะไฟดับไม่ได้วางแผน"}
          icon={Zap}
          tone="sky"
        />
        <KpiCard
          title="SAIFI (ความถี่เฉลี่ย)"
          value={kpis.saifi.toFixed(2)}
          unit="ครั้ง/ราย"
          subtext={yearFilter === "ALL" && y23 && y24 ? `2566: ${y23.saifi.toFixed(2)} → 2567: ${y24.saifi.toFixed(2)}` : "คำนวณจากฐานลูกค้าสายป้อน"}
          icon={Activity}
          tone="indigo"
        />
        <KpiCard
          title="SAIDI (เวลาดับเฉลี่ย)"
          value={kpis.saidi.toFixed(1)}
          unit="นาที/ราย"
          subtext={saidiPct !== null && yearFilter === "ALL" ? `YoY 2567 vs 2566: +${saidiPct}%` : "ผลกระทบรวมต่อผู้ใช้ไฟ 1 ราย"}
          icon={AlertTriangle}
          tone="rose"
        />
        <KpiCard
          title="CAIDI (เวลากู้คืนเฉลี่ย)"
          value={kpis.caidi.toFixed(1)}
          unit="นาที/ครั้ง"
          subtext={`มัธยฐานเวลาดับ ${kpis.medianDuration.toFixed(1)} นาที`}
          icon={Clock}
          tone="amber"
        />
        <KpiCard
          title="Customer-Minutes รวม"
          value={(kpis.customerMinutesSum / 1_000_000).toFixed(2)}
          unit="ล้านนาที-ราย"
          subtext={`ผู้ได้รับผลกระทบรวม ${kpis.customersAffectedSum.toLocaleString()} ราย-ครั้ง`}
          icon={Users}
          tone="emerald"
        />
      </div>

      {/* Row 1: YoY + Pareto */}
      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm print-break-inside-avoid">
          <h2 className="text-sm font-bold text-slate-900">
            1. เปรียบเทียบดัชนีความน่าเชื่อถือรายปี (2566 vs 2567)
          </h2>
          <p className="text-xs text-slate-500">
            เฉพาะ Unplanned Outages · แยกสลับรวม/ไม่รวมพายุเชียงรายได้จากแถบตัวกรองด้านบน
          </p>
          <div className="mt-3">
            <ChartWrapper height={270}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={yoySeries} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="year" tick={{ fontSize: 12 }} />
                  <YAxis yAxisId="left" tick={{ fontSize: 11 }} />
                  <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Bar yAxisId="left" dataKey="saidi" name="SAIDI (นาที/ราย/ปี)" fill="#e11d48" radius={[6, 6, 0, 0]} />
                  <Bar yAxisId="right" dataKey="saifi" name="SAIFI (ครั้ง/ราย/ปี)" fill="#0284c7" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartWrapper>
          </div>
          <StoryCard
            what="ปี 2567 ความน่าเชื่อถือแย่ลงชัดเจน: SAIDI เพิ่มจาก 817.0 เป็น 1,155.8 นาที (+41.5%) และเมื่อแยกพายุเชียงราย 22–23 ส.ค. ออก SAIDI ยังเพิ่มเป็น 897.3 นาที (+9.8%)"
            soWhat="พายุ 2 วันในเชียงรายอธิบาย ~76% ของ SAIDI ที่พุ่งขึ้น แต่ฐานความถี่ไฟดับปกติก็เพิ่มขึ้น +15.6% (SAIFI 6.32 → 7.30) แสดงถึงความเปราะบางสะสมของสายป้อน"
            nowWhat="ต้องแบ่งงบปี 2568 แก้ทั้งความเสี่ยงเชิงโครงสร้าง (ตัดแต่งต้นไม้ + เปลี่ยนอุปกรณ์เก่า) และตั้งแผนรองรับพายุในเชียงรายควบคู่กัน"
            limitation="ใช้ตัวหารผู้ใช้ไฟรวม 214,266 รายจากทะเบียนสายป้อนวันที่ 2025-01-05 (ประมาณค่าใน CMI-F02 และ LPG-F12) คงที่ทั้ง 2 ปี"
          />
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm print-break-inside-avoid">
          <h2 className="text-sm font-bold text-slate-900">
            2. Pareto สาเหตุไฟดับ: ความเสียหาย (ล้านนาที-ราย) vs สัดส่วนสะสม (%)
          </h2>
          <p className="text-xs text-slate-500">
            จัดอันดับตาม Customer-Minutes (ไม่ใช่แค่จำนวนครั้ง) เพื่อจัดลำดับงบประมาณที่ลด SAIDI ได้จริง
          </p>
          <div className="mt-3">
            <ChartWrapper height={270}>
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={pareto} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="label" tick={{ fontSize: 10 }} interval={0} angle={-15} textAnchor="end" height={50} />
                  <YAxis yAxisId="left" tick={{ fontSize: 11 }} />
                  <YAxis yAxisId="right" orientation="right" domain={[0, 100]} tick={{ fontSize: 11 }} unit="%" />
                  <Tooltip />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Bar yAxisId="left" dataKey="cmMillion" name="Customer-Minutes (ล้าน)" fill="#0f766e" radius={[6, 6, 0, 0]} />
                  <Line yAxisId="right" type="monotone" dataKey="cumCmPct" name="สัดส่วนสะสม (%)" stroke="#f59e0b" strokeWidth={2.5} dot={{ r: 3 }} />
                </ComposedChart>
              </ResponsiveContainer>
            </ChartWrapper>
          </div>
          <StoryCard
            what="ต้นไม้ (tree) สร้างผลกระทบสูงถึง 55.7% ของ customer-minutes ทั้งหมด (235.5 ล้านนาที-ราย) ตามด้วยอุปกรณ์ชำรุด (16.6%) ขณะที่สัตว์ (20.7% ของครั้ง) กินเพียง 5.6%"
            soWhat="เหตุจากสัตว์เกิดบ่อยแต่ดับสั้น (มัธยฐาน 55 นาที) ต่างจากต้นไม้ที่ดับนาน (166 นาที) หากดูแค่จำนวนครั้งจะจัดลำดับงบผิดเป้าหมาย"
            nowWhat="ทุ่มงบหลัก >70% ไปที่การจัดการต้นไม้ (tree) และเปลี่ยนอุปกรณ์เสื่อมสภาพ (equipment) ก่อน ส่วนสัตว์ใช้มาตรการต้นทุนต่ำเฉพาะจุด"
            limitation="มีเหตุการณ์ไม่ทราบสาเหตุ (unknown) 234 ครั้ง (9.0% ของครั้ง) ที่อาจปะปนสาเหตุต้นไม้หรืออุปกรณ์อยู่"
          />
        </section>
      </div>

      {/* Row 2: Monthly Trend + 24x7 Heatmap */}
      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm print-break-inside-avoid">
          <h2 className="text-sm font-bold text-slate-900">
            3. แนวโน้มจำนวนครั้งไฟดับรายเดือน (2566 vs 2567)
          </h2>
          <p className="text-xs text-slate-500">
            เปรียบเทียบฤดูกาล 12 เดือน เพื่อระบุหน้าต่างเวลาลงพื้นที่เชิงรุกก่อนเข้าฤดูฝน
          </p>
          <div className="mt-3">
            <ChartWrapper height={270}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={monthly} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Line type="monotone" dataKey="y2023Count" name="ปี 2566 (ครั้ง)" stroke="#64748b" strokeWidth={2} dot={{ r: 3 }} />
                  <Line type="monotone" dataKey="y2024Count" name="ปี 2567 (ครั้ง)" stroke="#dc2626" strokeWidth={2.5} dot={{ r: 3.5 }} />
                </LineChart>
              </ResponsiveContainer>
            </ChartWrapper>
          </div>
          <StoryCard
            what="58.8% ของไฟดับเกิดในฤดูฝน (พ.ค.–ต.ค.) และสูงสุดในเดือน ส.ค. (335 ครั้ง, 94.2 ล้านนาที-ราย) โดยเฉพาะเหตุต้นไม้ 67.7% และฟ้าผ่า 75.1% เกิดในช่วงนี้"
            soWhat="การตัดแต่งกิ่งไม้หลังเดือน พ.ค. ช้าเกินไปเพราะสายป้อนรับแรงลมฝนไปแล้ว ความเสียหายพุ่งสูงทันทีตั้งแต่ต้นฤดู"
            nowWhat="ล็อกตารางตัดแต่งกิ่งไม้และบำรุงรักษาเชิงป้องกันให้เสร็จภายใน มี.ค.–เม.ย. (ก่อนฤดูฝน) ทุกปี"
            limitation="เหตุการณ์ช่วงพายุใหญ่ ส.ค. 2567 มีความเข้มข้นผิดปกติเฉพาะ จ.เชียงราย จึงควรใช้ Toggle เปรียบเทียบทั้งแบบรวมและไม่รวมพายุ"
          />
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm print-break-inside-avoid">
          <h2 className="text-sm font-bold text-slate-900">
            4. แผนที่ความร้อนรายชั่วโมง × วันในสัปดาห์ (24×7 Heatmap)
          </h2>
          <p className="text-xs text-slate-500">
            ชี้จุดพีกตามช่วงเวลาของวัน (นำเมาส์ชี้เพื่อดูจำนวนครั้งและ customer-minutes)
          </p>
          <div className="mt-3">
            <Heatmap24x7 cells={heatmap.cells} maxCount={heatmap.maxCount} />
          </div>
          <StoryCard
            what="รูปแบบเวลาแยกตามสาเหตุชัดเจน: ฟ้าผ่า 67% และต้นไม้ 44.5% เกิดช่วงบ่าย–เย็น (14:00–18:59 น.) โหลดเกินพีก 14:00 น. ส่วนสัตว์ 46.1% กระจุกตัวตอนเช้า (05:00–09:59 น.)"
            soWhat="จัดเวรทีมช่างแบบคงที่ตลอด 24 ชม. ไม่สอดคล้องกับพีกช่วง 14:00–19:00 น. ทำให้เวลาตอบสนองและระยะเวลาดับสะสมสูงในช่วงเย็น"
            nowWhat="จัดกะทีมช่างเสริม (Standby Shift) ช่วง 13:30–20:00 น. ในฤดูฝน และติดอุปกรณ์กันสัตว์ในสายที่เกิดเหตุช่วง 05:00–09:59 น."
            limitation="เวลาเริ่มจาก Call Center/Mobile App อาจช้ากว่าเวลาตัดวงจรจริงใน SCADA เล็กน้อย และมี 3 เหตุการณ์ที่ไม่มีเวลาสิ้นสุด"
          />
        </section>
      </div>
    </div>
  );
}
