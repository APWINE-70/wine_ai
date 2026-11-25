"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { CheckCircle2, Target } from "lucide-react";
import ChartWrapper from "./ChartWrapper";
import StoryCard from "./StoryCard";

export default function ProposalsTab({ threeProjects }) {
  const chartData = [
    { name: "ฐานปี 2567 (Baseline)", saidi: threeProjects.baseline_2024_saidi_min, color: "#94a3b8" },
    ...threeProjects.projects.map((p) => ({
      name: `ลดจาก ${p.project_id}`,
      saidi: p.estimated_saidi_reduction_min,
      color: "#14b8a6",
    })),
    { name: "คาดการณ์หลัง 3 โครงการ", saidi: threeProjects.projected_2024_saidi_min, color: "#059669" },
  ];

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-2xl border border-emerald-100 bg-white p-4 shadow-sm shadow-emerald-950/[0.03]">
          <p className="text-xs text-slate-500">SAIDI ฐานปี 2567 (ก่อนปรับปรุง)</p>
          <p className="mt-1 text-2xl font-bold text-slate-700">
            {threeProjects.baseline_2024_saidi_min.toLocaleString()} <span className="text-xs font-normal">นาที/ราย/ปี</span>
          </p>
        </div>
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50/60 p-4 shadow-sm shadow-emerald-950/[0.03]">
          <p className="text-xs text-emerald-800">คาดการณ์ลด SAIDI รวม 3 โครงการ</p>
          <p className="mt-1 text-2xl font-bold text-emerald-700">
            -{threeProjects.estimated_total_saidi_reduction_min.toLocaleString()}{" "}
            <span className="text-xs font-normal">นาที (-{threeProjects.estimated_total_saidi_reduction_pct}%)</span>
          </p>
        </div>
        <div className="rounded-2xl border border-emerald-100 bg-white p-4 shadow-sm shadow-emerald-950/[0.03]">
          <p className="text-xs text-slate-500">SAIDI คาดการณ์หลังลงทุนปี 2568</p>
          <p className="mt-1 text-2xl font-bold text-emerald-700">
            {threeProjects.projected_2024_saidi_min.toLocaleString()} <span className="text-xs font-normal">นาที/ราย/ปี</span>
          </p>
        </div>
      </div>

      <section className="rounded-2xl border border-emerald-100 bg-white p-5 shadow-sm shadow-emerald-950/[0.03] print-break-inside-avoid">
        <div className="flex items-center gap-2">
          <Target className="h-4 w-4 text-emerald-700" />
          <h2 className="text-sm font-bold text-slate-900">
            จำลองผลลด SAIDI จาก 3 โครงการลงทุนปี 2568 (คำนวณบนฐานข้อมูลปี 2567)
          </h2>
        </div>
        <div className="mt-3">
          <ChartWrapper height={270}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} unit=" น." />
                <Tooltip />
                <Bar dataKey="saidi" name="SAIDI / ผลลด (นาที/ราย/ปี)" radius={[6, 6, 0, 0]}>
                  {chartData.map((entry, idx) => (
                    <Cell key={idx} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </ChartWrapper>
        </div>
        <StoryCard
          what={`3 โครงการเป้าหมายสามารถลด SAIDI รวมได้ ${threeProjects.estimated_total_saidi_reduction_min} นาที (-${threeProjects.estimated_total_saidi_reduction_pct}%) จาก ${threeProjects.baseline_2024_saidi_min} เหลือ ${threeProjects.projected_2024_saidi_min} นาที/ราย/ปี`}
          soWhat="โครงการ P1 (จัดการต้นไม้บน Top 5 สายป้อน) เพียงโครงการเดียวให้ผลลด SAIDI สูงถึง 71.3% ของผลลดทั้งหมด เพราะโจมตีจุดที่เกิดความเสียหายหนาแน่นที่สุด"
          nowWhat="อนุมัติงบตามลำดับความสำคัญ P1 (ทำก่อนฤดูฝน มี.ค.–เม.ย.) → P3 (เปลี่ยนอุปกรณ์ CMI-F14 + กันสัตว์) → P2 (ทีมช่างส่วนหน้าชนบทเชียงราย)"
          limitation="การจำลองใช้สมมติฐาน deterministic บนข้อมูลปี 2567 และยังไม่มีข้อมูลต้นทุน CAPEX/OPEX รายโครงการสำหรับคำนวณ Cost-per-SAIDI-minute"
        />
      </section>

      <div className="grid gap-4 lg:grid-cols-3">
        {threeProjects.projects.map((p) => (
          <div key={p.project_id} className="rounded-2xl border border-emerald-100 bg-white p-5 shadow-sm shadow-emerald-950/[0.03]">
            <div className="flex items-center justify-between">
              <span className="rounded-lg bg-emerald-100 px-2.5 py-1 text-xs font-bold text-emerald-800">
                {p.project_id} · สัดส่วนผลลัพธ์ {p.share_of_total_reduction_pct}%
              </span>
              <CheckCircle2 className="h-4 w-4 text-emerald-600" />
            </div>
            <h3 className="mt-3 text-sm font-bold text-slate-900">{p.title}</h3>
            <p className="mt-2 text-xs text-slate-600">
              <strong>ขอบเขต:</strong> {p.target_scope}
            </p>
            <p className="mt-1 text-xs text-slate-600">
              <strong>สมมติฐาน:</strong> {p.assumption}
            </p>
            <div className="mt-4 rounded-xl bg-emerald-50 p-3 text-xs text-emerald-900">
              คาดการณ์ลด SAIDI: <strong className="text-base">-{p.estimated_saidi_reduction_min}</strong> นาที/ราย/ปี
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
