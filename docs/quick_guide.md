# Quick Guide สำหรับคณะกรรมการ (Mission E)

> **ระบบ:** Lanna Power Grid Reliability — Executive Outage Analytics (2566–2567)  
> **ขอบเขตข้อมูล:** `2023-01-01` ถึง `2024-12-31 23:59` · **ทะเบียนสายป้อน:** `2025-01-05`

---

## 1. การเข้าใช้งานระบบ (URL & บัญชีทดสอบ)

- **Production URL (Vercel):** [https://wineai-one.vercel.app](https://wineai-one.vercel.app) *(สำรอง: [https://wineai-nrt6.vercel.app](https://wineai-nrt6.vercel.app))*
- **บัญชีทดสอบสำหรับกรรมการ (Test Account — กรอกให้อัตโนมัติบนหน้า Login):**
  - **Email:** `judge@lannapower.co.th`
  - **Password:** `Lanna2025!`

---

## 2. ขั้นตอนตรวจงานฉบับย่อ 1 นาที (Judge Walkthrough)

1. **เข้าสู่ระบบ:** กดปุ่ม **"เข้าสู่ระบบแดชบอร์ด"** บนหน้าแรก (ระบบกรอกบัญชีทดสอบไว้ให้พร้อมแล้ว)
2. **ตรวจหน้า Overview (ภารกิจ C & D):**
   - ดูการ์ด KPI หลักทั้ง 5 ตัว (Unplanned `2,594` ครั้ง, SAIFI, SAIDI, CAIDI, Customer-Minutes) และป้ายวันที่ข้อมูลถึง (`2024-12-31 23:59`)
   - กดปุ่ม **"รวมพายุ ส.ค.67 / แยกพายุ ส.ค.67 ออก"** เพื่อเปรียบเทียบผลพายุเชียงราย `22–23 ส.ค. 2567` (`79` เหตุการณ์, `+258.46` นาที SAIDI)
   - อ่านกล่องสรุป **What → So What → Now What + ข้อจำกัดข้อมูล** ใต้กราฟหลักทุกกราฟ (YoY, Pareto, Monthly Trend, 24×7 Heatmap)
3. **ทดลองตัวกรอง 5 มิติ & Export (ภารกิจ D):**
   - เลือกกรอง **ปี / จังหวัด / พื้นที่ / สายป้อน / สาเหตุ** แล้วกดปุ่ม **CSV** (เปิดภาษาไทยใน Excel ได้ทันที) หรือ **PDF**
   - ทดลองเลือกตัวกรองที่ขัดกัน (เช่น จังหวัดเชียงราย + สายป้อน `CMI-F01`) เพื่อดู **Empty State** พร้อมปุ่มล้างตัวกรอง
4. **ตรวจหน้า เจาะลึกรายสายป้อน / ข้อเสนอ 3 โครงการ / About (ภารกิจ F):**
   - แท็บ **เจาะลึกรายสายป้อน:** ดู Top 5 สายป้อนวิกฤต, สัญญาณเตือน **`CMI-F14` (+280%)**, สภาพอากาศ, และเวลากู้คืน
   - แท็บ **ข้อเสนอ 3 โครงการ:** ดูแบบจำลองลด SAIDI ปี 2568 (`1,155.79 → 836.43` นาที, **`-27.63%`**)
   - แท็บ **About & Performance:** ดูเวลา **First Load** และ **Filter Response Time (ms)** ที่วัดสดในเบราว์เซอร์ พร้อมปุ่มทดสอบ **Loading / Error State**

---

## 3. วิธีรันเวอร์ชันสำรองบนเครื่อง (Local Fallback)

### วิธีที่ 1: รันด้วยสคริปต์ (Windows — ไม่ต้องติดตั้ง Docker)
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_local.ps1
# หรือดับเบิลคลิกที่ scripts\run_local.bat
```
จากนั้นเปิดเบราว์เซอร์ไปที่ `http://127.0.0.1:3000`

### วิธีที่ 2: รันด้วย Docker
```powershell
docker build -t lanna-outage-dashboard .
docker run --rm -p 3000:80 lanna-outage-dashboard
```
เปิดเบราว์เซอร์ไปที่ `http://127.0.0.1:3000`

---

## 4. ขั้นตอน Deploy ขึ้น Vercel (สำหรับทีมส่งมอบ)

1. Push โค้ดขึ้น GitHub (`https://github.com/APWINE-70/wine_ai.git`)
2. เข้า [Vercel](https://vercel.com) → **Add New Project** → เลือก repo `APWINE-70/wine_ai`
3. ตั้งค่า **Root Directory** เป็น `web` (Vercel จะอ่าน `web/vercel.json` อัตโนมัติ: `npm run build` → `out`)
4. กด **Deploy** แล้วนำ Production URL ที่ได้มาอัปเดตในเอกสารส่งมอบและ Infographic
