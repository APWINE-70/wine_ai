"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  BarChart3,
  CloudLightning,
  Download,
  FilterX,
  Info,
  Layers,
  Loader2,
  LogOut,
  Printer,
  RefreshCw,
  RotateCcw,
  Target,
  Zap,
} from "lucide-react";
import dashboardData from "../data/dashboard_data.json";
import AboutTab from "../components/AboutTab";
import DrilldownTab from "../components/DrilldownTab";
import LoginGate from "../components/LoginGate";
import OverviewTab from "../components/OverviewTab";
import ProposalsTab from "../components/ProposalsTab";
import {
  CAUSE_LABELS,
  aggregateFeeders,
  aggregateHeatmap,
  aggregateMonthlyTrend,
  aggregateParetoByCause,
  computeKpis,
  exportEventsCsv,
  filterEvents,
  getDenominatorCustomers,
} from "../lib/analytics";

const DEFAULT_FILTERS = {
  year: "ALL",
  province: "ALL",
  feeder: "ALL",
  cause: "ALL",
  areaType: "ALL",
  includeStorm: true,
};

export default function DashboardPage() {
  const [authed, setAuthed] = useState(false);
  const [activeTab, setActiveTab] = useState("overview");
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [isLoading, setIsLoading] = useState(false);
  const [uiError, setUiError] = useState(null);

  const [perfStats, setPerfStats] = useState({
    firstLoadMs: null,
    lastFilterMs: 0,
    avgFilterMs: 0,
    filterCount: 0,
  });
  const filterTimesRef = useRef([]);

  useEffect(() => {
    if (typeof window !== "undefined") {
      if (window.sessionStorage.getItem("lanna_demo_auth") === "1" || window.location.search.includes("demo=1")) {
        setAuthed(true);
      }
      const navEntry = window.performance.getEntriesByType("navigation")[0];
      const measured = navEntry && navEntry.domContentLoadedEventEnd > 0
        ? navEntry.domContentLoadedEventEnd
        : window.performance.now();
      setPerfStats((prev) => ({ ...prev, firstLoadMs: Number(measured.toFixed(1)) }));
    }
  }, []);

  const handleLogin = () => {
    if (typeof window !== "undefined") {
      window.sessionStorage.setItem("lanna_demo_auth", "1");
    }
    setAuthed(true);
  };

  const handleLogout = () => {
    if (typeof window !== "undefined") {
      window.sessionStorage.removeItem("lanna_demo_auth");
    }
    setAuthed(false);
  };

  const updateFilter = (patch) => {
    const t0 = typeof performance !== "undefined" ? performance.now() : 0;
    setFilters((prev) => ({ ...prev, ...patch }));
    if (typeof performance !== "undefined") {
      requestAnimationFrame(() => {
        const dt = Math.max(0.1, performance.now() - t0);
        filterTimesRef.current.push(dt);
        const avg =
          filterTimesRef.current.reduce((a, b) => a + b, 0) /
          filterTimesRef.current.length;
        setPerfStats((prev) => ({
          ...prev,
          lastFilterMs: dt,
          avgFilterMs: avg,
          filterCount: filterTimesRef.current.length,
        }));
      });
    }
  };

  const provinces = useMemo(
    () => Array.from(new Set(dashboardData.feeders.map((f) => f.province))).sort(),
    []
  );
  const feederOptions = useMemo(() => {
    const list = dashboardData.feeders.filter((f) => {
      if (filters.province !== "ALL" && f.province !== filters.province) return false;
      if (filters.areaType !== "ALL" && f.area_type !== filters.areaType) return false;
      return true;
    });
    return list.map((f) => f.feeder_id).sort();
  }, [filters.province, filters.areaType]);

  const filteredEvents = useMemo(
    () => filterEvents(dashboardData.events, filters),
    [filters]
  );

  const denominatorCustomers = useMemo(
    () =>
      getDenominatorCustomers(
        dashboardData.feeders,
        filters,
        dashboardData.metadata.total_customers_served_imputed
      ),
    [filters]
  );

  const kpis = useMemo(
    () => computeKpis(filteredEvents, denominatorCustomers),
    [filteredEvents, denominatorCustomers]
  );

  const yoySeries = useMemo(() => {
    const baseNoYear = filterEvents(dashboardData.events, { ...filters, year: "ALL" });
    const e23 = baseNoYear.filter((e) => e.y === 2023);
    const e24 = baseNoYear.filter((e) => e.y === 2024);
    const k23 = computeKpis(e23, denominatorCustomers);
    const k24 = computeKpis(e24, denominatorCustomers);
    return [
      { year: "2566 (2023)", count: k23.count, saifi: Number(k23.saifi.toFixed(2)), saidi: Number(k23.saidi.toFixed(1)) },
      { year: "2567 (2024)", count: k24.count, saifi: Number(k24.saifi.toFixed(2)), saidi: Number(k24.saidi.toFixed(1)) },
    ];
  }, [filters, denominatorCustomers]);

  const pareto = useMemo(() => aggregateParetoByCause(filteredEvents), [filteredEvents]);
  const monthly = useMemo(() => aggregateMonthlyTrend(filteredEvents), [filteredEvents]);
  const heatmap = useMemo(() => aggregateHeatmap(filteredEvents), [filteredEvents]);
  const feederRows = useMemo(
    () => aggregateFeeders(filteredEvents, dashboardData.feeders),
    [filteredEvents]
  );

  if (!authed) {
    return <LoginGate onAuthenticated={handleLogin} />;
  }

  const tabs = [
    { id: "overview", label: "Overview (KPI & Story)", icon: BarChart3 },
    { id: "drilldown", label: "เจาะลึกรายสายป้อน / สาเหตุ", icon: Layers },
    { id: "proposals", label: "ข้อเสนอ 3 โครงการ (Q7)", icon: Target },
    { id: "about", label: "About & Performance (ภารกิจ F)", icon: Info },
  ];

  const handleSelectFeederFromDrilldown = (feederId) => {
    updateFilter({ feeder: feederId });
  };

  return (
    <div className="min-h-screen bg-[#f6fbf8]">
      {/* Top Navbar */}
      <header className="sticky top-0 z-30 border-b border-emerald-100 bg-white/95 backdrop-blur no-print">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-600 text-white shadow-sm shadow-emerald-600/20">
              <Zap className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-sm font-bold text-slate-900 sm:text-base">
                บริษัท ล้านนาพาวเวอร์ดิสทริบิวชัน จำกัด — Power Outage Analytics
              </h1>
              <p className="text-[11px] text-slate-500">
                ข้อมูลถึง: <strong className="text-emerald-700">{dashboardData.metadata.data_cutoff}</strong> · ทะเบียนสายป้อน:{" "}
                {dashboardData.metadata.feeder_export_date} · Unplanned 2,594 ครั้ง
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => exportEventsCsv(filteredEvents)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-200 bg-white px-2.5 py-1.5 text-xs font-medium text-emerald-800 hover:bg-emerald-50"
            >
              <Download className="h-3.5 w-3.5" />
              CSV
            </button>
            <button
              type="button"
              onClick={() => window.print()}
              className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-200 bg-white px-2.5 py-1.5 text-xs font-medium text-emerald-800 hover:bg-emerald-50"
            >
              <Printer className="h-3.5 w-3.5" />
              PDF
            </button>
            <button
              type="button"
              onClick={handleLogout}
              className="inline-flex items-center gap-1 rounded-lg bg-emerald-50 px-2.5 py-1.5 text-xs font-medium text-emerald-800 hover:bg-emerald-100"
            >
              <LogOut className="h-3.5 w-3.5" />
              ออก
            </button>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="mx-auto flex max-w-7xl gap-1.5 overflow-x-auto px-4 pb-2.5">
          {tabs.map((t) => {
            const Icon = t.icon;
            const active = activeTab === t.id;
            return (
              <button
                key={t.id}
                type="button"
                onClick={() => setActiveTab(t.id)}
                className={`inline-flex shrink-0 items-center gap-1.5 rounded-xl px-3.5 py-1.5 text-xs font-semibold transition ${
                  active
                    ? "bg-emerald-600 text-white shadow-sm shadow-emerald-600/20"
                    : "text-slate-600 hover:bg-emerald-50 hover:text-emerald-800"
                }`}
              >
                <Icon className="h-3.5 w-3.5" />
                {t.label}
              </button>
            );
          })}
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-6 px-4 py-5">
        {/* 5D Filter Bar + Storm Toggle */}
        <section className="rounded-2xl border border-emerald-100 bg-white p-4 shadow-sm shadow-emerald-950/[0.03] no-print">
          <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6">
            <div>
              <label className="block text-[11px] font-semibold text-slate-600">ปี (Year)</label>
              <select
                value={filters.year}
                onChange={(e) => updateFilter({ year: e.target.value })}
                className="mt-1 w-full rounded-lg border border-emerald-200 bg-white px-2.5 py-1.5 text-xs focus:border-emerald-500 focus:outline-none"
              >
                <option value="ALL">ทั้งหมด (2566–2567)</option>
                <option value="2023">ปี 2566 (2023)</option>
                <option value="2024">ปี 2567 (2024)</option>
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-slate-600">จังหวัด (Province)</label>
              <select
                value={filters.province}
                onChange={(e) => updateFilter({ province: e.target.value, feeder: "ALL" })}
                className="mt-1 w-full rounded-lg border border-emerald-200 bg-white px-2.5 py-1.5 text-xs focus:border-emerald-500 focus:outline-none"
              >
                <option value="ALL">ทุกจังหวัด (4 จังหวัด)</option>
                {provinces.map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-slate-600">พื้นที่ (Area Type)</label>
              <select
                value={filters.areaType}
                onChange={(e) => updateFilter({ areaType: e.target.value, feeder: "ALL" })}
                className="mt-1 w-full rounded-lg border border-emerald-200 bg-white px-2.5 py-1.5 text-xs focus:border-emerald-500 focus:outline-none"
              >
                <option value="ALL">ทุกพื้นที่</option>
                <option value="Urban">เขตเมือง (Urban)</option>
                <option value="Suburban">ชานเมือง (Suburban)</option>
                <option value="Rural">ชนบท (Rural)</option>
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-slate-600">สายป้อน (Feeder)</label>
              <select
                value={filters.feeder}
                onChange={(e) => updateFilter({ feeder: e.target.value })}
                className="mt-1 w-full rounded-lg border border-emerald-200 bg-white px-2.5 py-1.5 text-xs focus:border-emerald-500 focus:outline-none"
              >
                <option value="ALL">ทุกสายป้อน ({feederOptions.length})</option>
                {feederOptions.map((fid) => (
                  <option key={fid} value={fid}>{fid}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-slate-600">สาเหตุ (Cause)</label>
              <select
                value={filters.cause}
                onChange={(e) => updateFilter({ cause: e.target.value })}
                className="mt-1 w-full rounded-lg border border-emerald-200 bg-white px-2.5 py-1.5 text-xs focus:border-emerald-500 focus:outline-none"
              >
                <option value="ALL">ทุกสาเหตุ (7 กลุ่ม)</option>
                {Object.entries(CAUSE_LABELS).map(([k, lbl]) => (
                  <option key={k} value={k}>{lbl}</option>
                ))}
              </select>
            </div>

            <div className="flex flex-col justify-end gap-1.5">
              <button
                type="button"
                onClick={() => updateFilter({ includeStorm: !filters.includeStorm })}
                className={`inline-flex items-center justify-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-semibold transition ${
                  filters.includeStorm
                    ? "border-emerald-200 bg-emerald-50 text-emerald-800 hover:bg-emerald-100"
                    : "border-amber-400 bg-amber-100 text-amber-950 hover:bg-amber-200"
                }`}
              >
                <CloudLightning className="h-3.5 w-3.5" />
                {filters.includeStorm ? "รวมพายุ ส.ค.67" : "แยกพายุ ส.ค.67 ออก"}
              </button>
              <button
                type="button"
                onClick={() => updateFilter(DEFAULT_FILTERS)}
                className="inline-flex items-center justify-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-medium text-slate-600 hover:bg-emerald-50 hover:text-emerald-800"
              >
                <RotateCcw className="h-3 w-3" />
                ล้างตัวกรอง
              </button>
            </div>
          </div>
        </section>

        {/* UI State: Error */}
        {uiError ? (
          <div className="flex flex-col items-center justify-center rounded-2xl border border-rose-200 bg-rose-50 p-10 text-center">
            <AlertTriangle className="h-10 w-10 text-rose-600" />
            <h2 className="mt-3 text-base font-bold text-rose-950">เกิดข้อผิดพลาดในการโหลดข้อมูล</h2>
            <p className="mt-1 max-w-md text-xs text-rose-800">{uiError}</p>
            <button
              type="button"
              onClick={() => setUiError(null)}
              className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-rose-600 px-4 py-2 text-xs font-semibold text-white hover:bg-rose-700"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              ลองโหลดข้อมูลใหม่อีกครั้ง
            </button>
          </div>
        ) : isLoading ? (
          /* UI State: Loading */
          <div className="flex flex-col items-center justify-center rounded-2xl border border-emerald-100 bg-white p-14 text-center">
            <Loader2 className="h-9 w-9 animate-spin text-emerald-600" />
            <p className="mt-3 text-sm font-semibold text-slate-800">กำลังประมวลผลตัวชี้วัดและกราฟ...</p>
            <p className="mt-1 text-xs text-slate-500">กำลังคำนวณ SAIFI / SAIDI / CAIDI จากเหตุการณ์ Unplanned</p>
          </div>
        ) : filteredEvents.length === 0 ? (
          /* UI State: Empty */
          <div className="flex flex-col items-center justify-center rounded-2xl border border-emerald-100 bg-white p-12 text-center">
            <FilterX className="h-10 w-10 text-emerald-400" />
            <h2 className="mt-3 text-base font-bold text-slate-900">ไม่พบเหตุการณ์ไฟดับตามตัวกรองที่เลือก</h2>
            <p className="mt-1 max-w-md text-xs text-slate-500">
              เงื่อนไขที่เลือกอาจแคบเกินไป (เช่น สายป้อนในเขตเมืองที่เลือกพื้นที่เป็นชนบท) กรุณาลองล้างตัวกรองเพื่อดูข้อมูลทั้งหมด
            </p>
            <button
              type="button"
              onClick={() => updateFilter(DEFAULT_FILTERS)}
              className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-4 py-2 text-xs font-semibold text-white hover:bg-emerald-700"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              ล้างตัวกรองทั้งหมด
            </button>
          </div>
        ) : (
          /* Main Active Tab Content */
          <>
            {activeTab === "overview" ? (
              <OverviewTab
                kpis={kpis}
                yoySeries={yoySeries}
                pareto={pareto}
                monthly={monthly}
                heatmap={heatmap}
                includeStorm={filters.includeStorm}
                stormRecon={dashboardData.storm_reconciliation}
                yearFilter={filters.year}
              />
            ) : null}

            {activeTab === "drilldown" ? (
              <DrilldownTab
                feederRows={feederRows}
                agingAlerts={dashboardData.aging_alerts}
                weatherAnalysis={dashboardData.weather_analysis}
                restorationAnalysis={dashboardData.restoration_analysis}
                onSelectFeeder={handleSelectFeederFromDrilldown}
                onExportCsv={() => exportEventsCsv(filteredEvents)}
                onPrintPdf={() => window.print()}
              />
            ) : null}

            {activeTab === "proposals" ? (
              <ProposalsTab threeProjects={dashboardData.three_projects} />
            ) : null}

            {activeTab === "about" ? (
              <AboutTab
                perfStats={perfStats}
                metadata={dashboardData.metadata}
                reliability={dashboardData.reliability}
                onSimulateLoading={() => {
                  setIsLoading(true);
                  setTimeout(() => setIsLoading(false), 900);
                }}
                onSimulateError={() =>
                  setUiError("จำลองเหตุการณ์โหลดชุดข้อมูลไม่สำเร็จ: ตรวจสอบการเชื่อมต่อหรือกดปุ่มด้านล่างเพื่อกู้คืน")
                }
              />
            ) : null}
          </>
        )}
      </main>
    </div>
  );
}
