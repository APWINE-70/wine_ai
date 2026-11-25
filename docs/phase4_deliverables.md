# สรุปชุดเอกสารส่งมอบและการนำเสนอ (Phase 4: Mission E & Deliverables)

> **กำหนดส่ง Day 1:** ภายใน `16:30 น.` (ระบบ + แพ็ก `.zip` + Infographic + Quick Guide)  
> **กำหนดส่ง Day 2:** ภายใน `12:00 น.` (สไลด์นำเสนอ ≤ 12 หน้า)

---

## 1. รายการไฟล์ที่จัดทำในเฟสที่ 4

| รายการตามแผน (4.1–4.4) | ไฟล์ที่สร้าง | รายละเอียดและสถานะ |
|---|---|---|
| **4.1 Deploy (Vercel) & Fallback** | [web/vercel.json](../web/vercel.json)<br>[Dockerfile](../Dockerfile)<br>[scripts/run_local.ps1](../scripts/run_local.ps1)<br>[scripts/run_local.bat](../scripts/run_local.bat)<br>[docs/quick_guide.md](quick_guide.md) | ตั้งค่า Static Export สำหรับ Vercel (`output: "export"` → `out/`), เตรียม Multi-stage Nginx `Dockerfile`, สคริปต์รันบน Windows (`http://127.0.0.1:3000`), และ Quick Guide พร้อมบัญชีทดสอบ `judge@lannapower.co.th` / `Lanna2025!` |
| **4.2 อินโฟกราฟิกคู่มือ 1 หน้า** | [deliverables/infographic_user_manual.html](../deliverables/infographic_user_manual.html)<br>[deliverables/infographic_user_manual.pdf](../deliverables/infographic_user_manual.pdf)<br>[deliverables/infographic_user_manual.png](../deliverables/infographic_user_manual.png) | คู่มือใช้งาน A4 1 หน้า ครบทั้งบัญชีทดสอบ, ตัวกรอง 5 มิติ, 4 หน้าจอหลัก, นิยาม SAIFI/SAIDI/CAIDI, ข้อจำกัดข้อมูล และสรุป 3 โครงการ (เรนเดอร์เป็น PDF และ PNG แล้ว) |
| **4.3 สไลด์นำเสนอ 12 หน้า (10 นาที)** | [deliverables/presentation_slides.md](../deliverables/presentation_slides.md)<br>[deliverables/slides.html](../deliverables/slides.html)<br>[deliverables/presentation_slides.pdf](../deliverables/presentation_slides.pdf) | เรียงตาม **ปัญหา/เป้าหมาย (1–2) → วิธีทำ (3–5) → ข้อค้นพบ (6–9) → ข้อเสนอแนะ & ระบบ (10–12)** พร้อมบทพูดประมาณ ~45–50 วินาที/สไลด์ |
| **4.4 แพ็กงานข้อมูล (`.zip`)** | [scripts/build_submission_zip.py](../scripts/build_submission_zip.py)<br>[lanna_power_outage_submission.zip](../lanna_power_outage_submission.zip) | ตรวจเช็กไฟล์บังคับและแพ็กโครงสร้าง `data/raw/`, `data/clean/`, `sample/`, `src/`, `docs/`, `deliverables/`, `scripts/`, `tests/`, `web/` (ยกเว้น `node_modules` / `.next` / `out`) |

---

## 2. ขั้นตอนนำระบบขึ้น Production URL จริง (Vercel)

เนื่องจากยังไม่ได้ผูก Vercel CLI บนเครื่องนี้ การเผยแพร่ขึ้น Production URL สามารถทำได้ 2 วิธี:

1. **เชื่อมผ่าน GitHub (แนะนำ):**
   - Push โค้ดจาก `C:\Apai` ขึ้น `https://github.com/APWINE-70/wine_ai.git` (`git push -u origin main`)
   - เข้า Vercel → **Add New Project** → Import `APWINE-70/wine_ai` → ตั้ง **Root Directory = `web`** → กด **Deploy**
2. **หรือใช้ Vercel CLI:**
   ```powershell
   cd C:\Apai\web
   npx vercel --prod
   ```
3. เมื่อได้ URL จริงแล้ว ให้นำมาเติมแทน `<ระบุ URL หลัง Deploy ขึ้น Vercel>` ใน [docs/quick_guide.md](quick_guide.md)

---

## 3. คำสั่งทดสอบและแพ็กส่งมอบซ้ำ

```powershell
# 1. ทดสอบชุดคำสั่งทั้งหมด (Phase 1 & Phase 2 invariants)
python -m unittest discover -s tests -v

# 2. รันเวอร์ชันสำรองบนเครื่อง Windows (เปิด http://127.0.0.1:3000)
powershell -ExecutionPolicy Bypass -File .\scripts\run_local.ps1

# 3. สร้างแพ็กเกจ .zip ส่งมอบใหม่
python -m scripts.build_submission_zip
```
