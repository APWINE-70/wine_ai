export const CAUSE_LABELS = {
  tree: "ต้นไม้ (Tree)",
  equipment: "อุปกรณ์ชำรุด (Equipment)",
  lightning: "ฟ้าผ่า (Lightning)",
  vehicle: "รถชนเสา (Vehicle)",
  animal: "สัตว์ (Animal)",
  unknown: "ไม่ทราบสาเหตุ (Unknown)",
  overload: "โหลดเกิน (Overload)",
};

export const MONTH_LABELS = [
  "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
  "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค.",
];

export function filterEvents(events, filters) {
  return events.filter((ev) => {
    if (!filters.includeStorm && ev.storm) return false;
    if (filters.year !== "ALL" && String(ev.y) !== filters.year) return false;
    if (filters.province !== "ALL" && ev.p !== filters.province) return false;
    if (filters.feeder !== "ALL" && ev.f !== filters.feeder) return false;
    if (filters.cause !== "ALL" && ev.c !== filters.cause) return false;
    if (filters.areaType !== "ALL" && ev.a !== filters.areaType) return false;
    return true;
  });
}

export function getDenominatorCustomers(feeders, filters, systemTotalCustomers) {
  if (
    filters.province === "ALL" &&
    filters.feeder === "ALL" &&
    filters.areaType === "ALL"
  ) {
    return systemTotalCustomers;
  }
  const matched = feeders.filter((f) => {
    if (filters.province !== "ALL" && f.province !== filters.province) return false;
    if (filters.feeder !== "ALL" && f.feeder_id !== filters.feeder) return false;
    if (filters.areaType !== "ALL" && f.area_type !== filters.areaType) return false;
    return true;
  });
  const sum = matched.reduce((acc, f) => acc + (f.customers_served || 0), 0);
  return sum > 0 ? sum : systemTotalCustomers;
}

export function computeKpis(events, denominator) {
  let custSum = 0;
  let cmSum = 0;
  const durations = [];

  for (const ev of events) {
    custSum += ev.cust;
    cmSum += ev.cm;
    durations.push(ev.dur);
  }
  durations.sort((a, b) => a - b);
  const mid = Math.floor(durations.length / 2);
  const medianDuration =
    durations.length === 0
      ? 0
      : durations.length % 2 !== 0
      ? durations[mid]
      : (durations[mid - 1] + durations[mid]) / 2;

  const saifi = denominator > 0 ? custSum / denominator : 0;
  const saidi = denominator > 0 ? cmSum / denominator : 0;
  const caidi = saifi > 0 ? saidi / saifi : 0;

  return {
    count: events.length,
    customersAffectedSum: custSum,
    customerMinutesSum: cmSum,
    medianDuration,
    saifi,
    saidi,
    caidi,
  };
}

export function aggregateParetoByCause(events) {
  const map = new Map();
  let totalCm = 0;
  for (const ev of events) {
    totalCm += ev.cm;
    const prev = map.get(ev.c) || { cause: ev.c, label: CAUSE_LABELS[ev.c] || ev.c, count: 0, cm: 0 };
    prev.count += 1;
    prev.cm += ev.cm;
    map.set(ev.c, prev);
  }
  const rows = Array.from(map.values()).sort((a, b) => b.cm - a.cm);
  let cumCm = 0;
  return rows.map((r) => {
    cumCm += r.cm;
    return {
      ...r,
      cmMillion: Number((r.cm / 1_000_000).toFixed(2)),
      cmSharePct: totalCm > 0 ? Number(((r.cm / totalCm) * 100).toFixed(1)) : 0,
      cumCmPct: totalCm > 0 ? Number(((cumCm / totalCm) * 100).toFixed(1)) : 0,
      countSharePct: events.length > 0 ? Number(((r.count / events.length) * 100).toFixed(1)) : 0,
    };
  });
}

export function aggregateMonthlyTrend(events) {
  const byMonth = Array.from({ length: 12 }, (_, idx) => ({
    month: idx + 1,
    label: MONTH_LABELS[idx],
    y2023Count: 0,
    y2024Count: 0,
    y2023CmM: 0,
    y2024CmM: 0,
  }));
  for (const ev of events) {
    const row = byMonth[ev.m - 1];
    if (!row) continue;
    if (ev.y === 2023) {
      row.y2023Count += 1;
      row.y2023CmM += ev.cm / 1_000_000;
    } else if (ev.y === 2024) {
      row.y2024Count += 1;
      row.y2024CmM += ev.cm / 1_000_000;
    }
  }
  return byMonth.map((r) => ({
    ...r,
    y2023CmM: Number(r.y2023CmM.toFixed(2)),
    y2024CmM: Number(r.y2024CmM.toFixed(2)),
  }));
}

export function aggregateHeatmap(events) {
  const map = new Map();
  let maxCount = 0;
  for (const ev of events) {
    const key = `${ev.d}-${ev.h}`;
    const prev = map.get(key) || { dow: ev.d, hour: ev.h, count: 0, cm: 0 };
    prev.count += 1;
    prev.cm += ev.cm;
    if (prev.count > maxCount) maxCount = prev.count;
    map.set(key, prev);
  }
  return { cells: Array.from(map.values()), maxCount };
}

export function aggregateFeeders(events, feedersMeta) {
  const metaMap = new Map(feedersMeta.map((f) => [f.feeder_id, f]));
  const map = new Map();
  let totalCm = 0;
  for (const ev of events) {
    if (ev.orp) continue;
    totalCm += ev.cm;
    const prev = map.get(ev.f) || {
      feeder_id: ev.f,
      count: 0,
      count2023: 0,
      count2024: 0,
      equip2023: 0,
      equip2024: 0,
      cm: 0,
      durations: [],
    };
    prev.count += 1;
    if (ev.y === 2023) prev.count2023 += 1;
    if (ev.y === 2024) prev.count2024 += 1;
    if (ev.c === "equipment" && ev.y === 2023) prev.equip2023 += 1;
    if (ev.c === "equipment" && ev.y === 2024) prev.equip2024 += 1;
    prev.cm += ev.cm;
    prev.durations.push(ev.dur);
    map.set(ev.f, prev);
  }

  return Array.from(map.values())
    .map((r) => {
      const meta = metaMap.get(r.feeder_id) || {};
      r.durations.sort((a, b) => a - b);
      const mid = Math.floor(r.durations.length / 2);
      const medianDur = r.durations.length ? r.durations[mid] : 0;
      const len = meta.length_km || 0;
      return {
        feeder_id: r.feeder_id,
        province: meta.province || "-",
        area_type: meta.area_type || "-",
        length_km: len,
        customers_served: meta.customers_served || 0,
        tree_cover: meta.tree_cover || "-",
        install_year: meta.install_year || "-",
        count: r.count,
        count2023: r.count2023,
        count2024: r.count2024,
        equip2023: r.equip2023,
        equip2024: r.equip2024,
        medianDur,
        cm: r.cm,
        cmMillion: Number((r.cm / 1_000_000).toFixed(2)),
        cmSharePct: totalCm > 0 ? Number(((r.cm / totalCm) * 100).toFixed(2)) : 0,
        ratePer100KmYr: len > 0 ? Number(((r.count / (len * 2)) * 100).toFixed(1)) : 0,
      };
    })
    .sort((a, b) => b.cm - a.cm);
}

export function exportEventsCsv(events, filename = "lanna_outages_filtered.csv") {
  const headers = [
    "outage_id", "date", "year", "month", "hour", "feeder_id",
    "province", "area_type", "cause", "duration_min",
    "customers_affected", "customer_minutes", "crew_arrival_min", "is_cri_storm_2024_08",
  ];
  const lines = [headers.join(",")];
  for (const ev of events) {
    lines.push([
      ev.id,
      ev.dt,
      ev.y,
      ev.m,
      ev.h,
      ev.f,
      ev.p || "",
      ev.a || "",
      ev.c,
      ev.dur,
      ev.cust,
      ev.cm,
      ev.crew ?? "",
      ev.storm ? "true" : "false",
    ].join(","));
  }
  const blob = new Blob(["\uFEFF" + lines.join("\n")], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
