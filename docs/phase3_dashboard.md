# สรุปการพัฒนาเว็บแดชบอร์ด (Phase 3: Missions C, D, F)

> **โค้ดเว็บแอปพลิเคชัน:** `web/` (Next.js 14.2.25 Static Export + Tailwind CSS + Recharts + Lucide Icons)  
> **สคริปต์ส่งออกข้อมูลเว็บ:** [src/export_web_data.py](../src/export_web_data.py) → [web/src/data/dashboard_data.json](../web/src/data/dashboard_data.json) (`589.8 KB`, 2,594 เหตุการณ์ Unplanned + 54 สายป้อน)

---

## 1. สถาปัตยกรรมและโครงสร้างไฟล์ (`web/`)

| ไฟล์ / คอมโพเนนต์ | หน้าที่หลัก | เกณฑ์ที่รองรับ |
|---|---|---|
| [web/next.config.mjs](../web/next.config.mjs) | ตั้งค่า `output: "export"` และ `images: { unoptimized: true }` สร้าง Static Site เต็มรูปแบบลง `web/out/` | Mission E, F |
| [web/src/app/layout.jsx](../web/src/app/layout.jsx) & [globals.css](../web/src/app/globals.css) | Root layout พร้อม `suppressHydrationWarning`, ฟอนต์ Noto Sans Thai / Inter และ `@media print` สำหรับ Export PDF | Mission D, C |
| [web/src/components/ChartWrapper.jsx](../web/src/components/ChartWrapper.jsx) | Client-only mount guard (`mounted` state ใน `useEffect`) ป้องกัน Recharts SSR Hydration Error #423 | Stability |
| [web/src/components/LoginGate.jsx](../web/src/components/LoginGate.jsx) | หน้าเข้าสู่ระบบพร้อมบัญชีทดสอบกรรมการ (`judge@lannapower.co.th` / `Lanna2025!`) | Mission E |
| [web/src/components/StoryCard.jsx](../web/src/components/StoryCard.jsx) | กล่องสรุป **What → So What → Now What** พร้อมระบุ **ข้อจำกัดของข้อมูล** ใต้กราฟหลักทุกตัว | Mission C (20 คะแนน) |
| [web/src/components/Heatmap24x7.jsx](../web/src/components/Heatmap24x7.jsx) | แผนที่ความร้อน 24 ชั่วโมง × 7 วัน แสดงจุดพีกของความถี่และ customer-minutes | Mission B, C |
| [web/src/components/OverviewTab.jsx](../web/src/components/OverviewTab.jsx) | KPI Cards (Unplanned, SAIFI, SAIDI, CAIDI, Customer-Minutes), Banner พายุ ส.ค.67, YoY Bar, Pareto, Monthly Trend, 24×7 Heatmap | Mission C, D |
| [web/src/components/DrilldownTab.jsx](../web/src/components/DrilldownTab.jsx) | Top 10 Feeders (คลิกกรองได้), Alert `CMI-F14` (+280%), กราฟอากาศ/การกู้คืน, ตารางสายป้อน 54 สาย | Mission C, D |
| [web/src/components/ProposalsTab.jsx](../web/src/components/ProposalsTab.jsx) | จำลองผล 3 โครงการลด SAIDI ปี 2568 (`1,155.79 → 836.43` นาที, `-27.63%`) | Mission C, Q7 |
| [web/src/components/AboutTab.jsx](../web/src/components/AboutTab.jsx) | แสดงผลการวัด First Load / Filter Response Time สด, ตารางก่อน–หลังคลีน, และปุ่มทดสอบ Loading/Error State | Mission D, F |
| [web/src/lib/analytics.js](../web/src/lib/analytics.js) | ฟังก์ชันกรอง 5 มิติ + Toggle พายุ, คำนวณ SAIFI/SAIDI/CAIDI, และ Export CSV (UTF-8 BOM เปิดภาษาไทยใน Excel ได้ทันที) | Mission D, F |
| [web/src/app/page.jsx](../web/src/app/page.jsx) | ศูนย์ควบคุม Navigation, แถบตัวกรอง 5 มิติ, ป้าย `ข้อมูลถึง: 2024-12-31 23:59`, Loading/Empty/Error States | Mission C, D |

---

## 2. สรุปฟีเจอร์ตามเกณฑ์คะแนน (Missions C, D, F)

### ภารกิจ C: สื่อสารด้วยกราฟ (20 คะแนน)
- เลือกชนิดกราฟตรงกับคำถาม: Grouped Bar (YoY), Composed Pareto (Bar + Cumulative % Line), Multi-line (Seasonal Monthly), 24×7 Matrix Heatmap, Horizontal Bar (Top 10 Feeders), Comparison Bar (Weather Tiers & Restoration by Area Type), Waterfall/Comparison Bar (3 Projects)
- มี **What → So What → Now What + ข้อจำกัดข้อมูล** ใต้กราฟหลักครบทุกกราฟ
- ตัวเลข KPI และกราฟคำนวณจากชุดข้อมูลเดียวกับ [docs/web_analytics.json](web_analytics.json) และ [docs/executive_answers.md](executive_answers.md) พร้อมแสดงวันที่ข้อมูลถึง (`2024-12-31 23:59`) บน Header

### ภารกิจ D: การใช้งานเว็บ (6 คะแนน)
- เชื่อมโยงจาก **Overview (KPI)** → **เจาะลึกรายสายป้อน / สาเหตุ** → **ข้อเสนอ 3 โครงการ** → **About & Performance**
- **ตัวกรอง 5 มิติ:** ปี (`2566/2567`), จังหวัด (4 จังหวัด), พื้นที่ (`Urban/Suburban/Rural`), สายป้อน (`54` สาย), สาเหตุ (`7` กลุ่ม) + **Toggle รวม/แยกพายุเชียงราย 22–23 ส.ค. 2567**
- **Export:** ปุ่ม **CSV** (พร้อม UTF-8 BOM) และ **PDF** (`window.print()` พร้อม `@media print` ซ่อนแถบเมนูและจัดหน้าอัตโนมัติ)
- **สถานะระบบ:** มีครบทั้ง **Loading State**, **Empty State** (พร้อมปุ่มล้างตัวกรองเมื่อผลลัพธ์เป็น 0), และ **Error State** (พร้อมปุ่มลองโหลดใหม่ + ปุ่มจำลองทดสอบในหน้า About)

### ภารกิจ F: ประสิทธิภาพและการวัดผลจริง (5 คะแนน)
- **ผลการ build (`cmd /c npm run build`):**
  - คอมไพล์ Static SSG (`○ /`) สำเร็จโดยไม่มี error
  - Route `/`: **`190 kB`** · **First Load JS = `277 kB`** (Shared chunks `87.3 kB`)
  - ทดสอบเสิร์ฟไฟล์ static `web/out/index.html` ผ่าน local HTTP server: **`HTTP 200`**, ขนาดรวมทั้งโฟลเดอร์ **`1,750.6 KB`**, เวลาตอบสนอง **`157.63 ms` (`0.158 วินาที`)** (< `0.3 วินาที`)
- **เทคนิคที่ทำให้โหลดเร็ว (< 0.3 วินาที):**
  1. **Python Pre-aggregation:** ยุบข้อมูล 4 ตารางและคำนวณค่าสถิติล่วงหน้าใน `dashboard_data.json`
  2. **Next.js Static Export:** Pre-render HTML ทันทีโดยไม่มี Backend Cold Start
  3. **Client `useMemo` Filtering:** คำนวณตัวกรอง 5 มิติบน 2,594 เหตุการณ์ในหน่วยความจำและวัดเวลาจริงด้วย `performance.now()` แสดงผลสดในหน้า **About**

---

## 3. คำสั่งรันและตรวจสอบบนเครื่อง

```powershell
# 1. สร้างชุดข้อมูล JSON สำหรับเว็บ (หากมีการอัปเดตข้อมูลสะอาด)
python -m src.export_web_data

# 2. รันโหมดพัฒนา (Dev Server)
cd C:\Apai\web
cmd /c npm run dev

# 3. สร้าง Static Production Build (ผลลัพธ์อยู่ใน C:\Apai\web\out)
cd C:\Apai\web
cmd /c npm run build
```
