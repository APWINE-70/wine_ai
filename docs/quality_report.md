# รายงานการตรวจสอบคุณภาพข้อมูล 4 มิติ (Mission N: ICT-DRMC-384B)

> สร้างอัตโนมัติจากข้อมูลดิบใน `data/raw/` โดยไม่มีการแก้ไขไฟล์ต้นฉบับ (ตรวจสอบก่อนทำ Mission B)

## 1. สรุปจำนวนแถวดิบตั้งต้นและค่าว่าง

| ตาราง | จำนวนแถวดิบ | ค่าว่างรายคอลัมน์ |
|---|---:|---|
| `outages_raw` | 2,843 | `end_time`: 91, `duration_min`: 116, `customers_affected`: 70, `cause`: 74, `crew_arrival_min`: 288 |
| `feeders` | 55 | `customers_served`: 2 |
| `substations` | 8 | ไม่พบค่าว่าง |
| `weather_daily` | 2,899 | ไม่พบค่าว่าง |

- **Weather completeness:** คาดหวัง `2,924` province-days (731 วัน × 4 จังหวัด), พบจริงไม่ซ้ำ `2,899` และขาดหาย **25** province-days

## 2. สรุปปัญหาทั้ง 4 มิติ (จำนวนแถว วิธีตรวจ วิธีแก้ และข้อเสนอต่อระบบต้นทาง)

| มิติ | ประเภทปัญหา | จำนวนแถว | วิธีตรวจ | วิธีแก้ใน Pipeline | ข้อเสนอแนะถึงเจ้าของระบบต้นทาง |
|---|---|---:|---|---|---|
| **Completeness** | `outages.end_time` ว่าง | 91 | ตรวจค่าว่าง/null token | คำนวณคืนจาก `start_time + duration_min` | SCADA: บังคับบันทึกเวลาปิดงานทุกเหตุการณ์ |
| **Completeness** | `outages.duration_min` ว่าง | 116 | ตรวจค่าว่าง/null token | คำนวณคืนจาก `end_time - start_time` | SCADA: คำนวณ duration อัตโนมัติจาก timestamp |
| **Completeness** | ว่างทั้ง `end_time` และ `duration_min` | 3 | ตรวจร่วม 2 คอลัมน์ | ติดธงและทำ dual reporting (ตัดออก vs impute median) | ระบบรับแจ้งเหตุ: ป้องกันการปิดใบงานโดยไม่มีเวลาสิ้นสุด |
| **Completeness** | `outages.customers_affected` ว่าง / N/A / - / ไม่ระบุ | 70 | ตรวจหลัง normalize null tokens | ติดธงและทำ sensitivity check (ตัดออก vs impute median สายป้อน) | ศูนย์รับแจ้งเหตุ: เชื่อมจำนวนลูกค้าจาก GIS ตามจุดตัดไฟ |
| **Completeness** | `feeders.Customers` ว่าง | 2 | ตรวจทะเบียนสายป้อน | ประมาณค่าตามค่ามัธยฐานกลุ่ม Area Type และรายงานผลกระทบต่อ SAIFI | GIS: ตรวจความครบถ้วนของจำนวนมิเตอร์ก่อน export |
| **Completeness** | ข้อมูลอากาศรายวันขาดหาย (province-days) | 25 | Cross-join ปฏิทิน 2023–2024 × 4 จังหวัด | ใช้ Left Join เพื่อไม่ให้เหตุการณ์ไฟดับหล่น | กรมอุตุฯ / ETL: ตั้ง alert และ backfill รายวัน |
| **Accuracy** | `start_time` / `end_time` สลับกัน (`end < start`) | 14 | ตรวจ `end_time < start_time` | สลับเวลาคืนและคำนวณ duration ใหม่เป็นบวก | ศูนย์รับแจ้งเหตุ: เพิ่ม validation ห้ามเวลาสิ้นสุดน้อยกว่าเริ่ม |
| **Accuracy** | `duration_min` บันทึกเป็นชั่วโมง | 42 | ตรวจ `(dur * 60) ≈ (end - start)` | แทนที่ด้วย `(end_time - start_time)` หน่วยนาที | ระบบรับแจ้งเหตุ: ระบุหน่วย `(นาที)` ชัดเจนและล็อกการคำนวณ |
| **Accuracy** | `duration_min` เป็นค่า placeholder/เกินจริง (`>= 9999`) | 8 | ตรวจค่า `9999 / 99999 / 14400` | ล้างเป็น missing แล้วรายงานแบบ Strict vs Imputed | SCADA: ห้ามใช้ค่า `9999` แทนค่าว่าง ให้ใช้ `NULL` |
| **Accuracy** | `customers_affected` เกินจำนวนลูกค้าทั้งสายป้อน | 16 | เทียบ `customers_affected > feeder.Customers` | ล้างค่าเกินจริง (เก็บ raw ไว้) และเทียบผลก่อน–หลังแก้ | SCADA/Call Center: บังคับเพดานไม่เกินจำนวนลูกค้าใน GIS |
| **Accuracy** | `crew_arrival_min` ติดลบ | 8 | ตรวจ `< 0` | แปลงเป็น `NaN` (หมายเหตุ: `crew > duration` เป็นเหตุการณ์จริงเมื่อกู้ระบบผ่าน SCADA ก่อนช่างถึง) | ระบบภาคสนาม: ห้ามเวลาเดินทางติดลบ |
| **Accuracy** | `feeders.Length` บันทึกเป็นเมตร (`> 1000`) | 4 | ตรวจความยาวสาย `> 1000` กม. | หารด้วย `1,000` แปลงเป็นกิโลเมตร | GIS: บังคับหน่วย `km` ก่อนส่งออก |
| **Accuracy** | อุณหภูมิลำพูนเป็น °F (`> 50`) | 60 | ตรวจ `max_temp_c > 50` (พบช่วง 84–95.5 °F) | แปลง `(F - 32) × 5/9` เป็น °C | กรมอุตุฯ / ETL: ตรวจช่วงค่าและหน่วย °C ก่อน ingest |
| **Accuracy** | ปริมาณฝน sentinel `-999` | 40 | ตรวจ `rainfall_mm < 0` | แทนที่ `-999` ด้วย `NaN` เพื่อไม่ให้บิดเบือนค่าเฉลี่ย/สหสัมพันธ์ | กรมอุตุฯ / ETL: แปลงรหัส error `-999` เป็น `NULL` |
| **Accuracy** | Extreme duration ที่เกิดจริง (`> Q3 + 3×IQR`) | 55 | Tukey fence (665.0 นาที) | เก็บไว้ในชุด clean และรายงานคู่ **รวม vs ไม่รวมพายุ** | แยก flag เหตุการณ์ภัยพิบัติระดับจังหวัด |
| **Consistency** | แถวซ้ำทุกคอลัมน์ใน `outages_raw` | 68 | `duplicated()` ทุกคอลัมน์ | ลบแถวซ้ำแบบ deterministic และบันทึกใน `audit_log.json` | ETL กลาง: ทำ idempotent ingestion |
| **Consistency** | ซ้ำบน business key (`feeder_id + start_time`) | 32 | ตรวจซ้ำข้าม `OUT-*` และ `OUT-CC-*` | รวมเหตุการณ์ซ้ำข้ามช่องทางและนับจำนวนใน log | SCADA + Call Center: ผูก Master Incident ID เดียวกัน |
| **Consistency** | รูปแบบ `feeder_id` ไม่มาตรฐาน | 111 | Regex `^[A-Z]{3}-?F(\d+)$` | แปลงเป็น `XXX-FNN` ก่อนตรวจ FK | ทุกระบบ: ใช้ dropdown รหัสสายป้อนมาตรฐาน |
| **Consistency** | `feeders` แถวซ้ำ (`CMI-F18`) และ `substations.capacity_mva` มีหน่วยข้อความ | 2 | `duplicated()` บนทะเบียนสายป้อน + regex ตรวจหน่วย | ลบแถวซ้ำ (`55 → 54`) และแยกตัวเลข `75.0` MVA | GIS: บังคับ PK และแยกคอลัมน์หน่วยวัดออกจากตัวเลข |
| **Consistency** | รหัส FK กำพร้า (`outages.feeder_id` หลัง normalize) | 10 | Set difference กับทะเบียนสายป้อน | เก็บเหตุการณ์ไว้และแยก flag สำหรับรายงานระดับสายป้อน vs ทั้งระบบ | GIS/SCADA: บังคับ Referential Integrity |
| **Consistency** | ปี พ.ศ. (`dd/mm/YYYY` ≥ 2400) | 500 | Regex ตรวจปี >= 2400 | แปลง `year - 543` แบบ day-first | ทุกระบบ: ใช้ ISO-8601 ค.ศ. |
| **Timeliness** | ปีพิมพ์ผิดอยู่นอกช่วงข้อมูล (2014, 2042, 2204) | 5 | ตรวจ `start_time` นอก 2023–2024 | กู้ปีที่ถูกต้องจาก `outage_id` / `end_time` พร้อมบันทึก flag | ระบบรับแจ้งเหตุ: ล็อกช่วงวันที่รับข้อมูลให้ตรงกับปีปฏิบัติการ |
| **Timeliness** | ทะเบียนสายป้อนส่งออกวันที่ `2025-01-05` หลังสิ้นสุดข้อมูลไฟดับ (`2024-12-31`) | 54 สายป้อน | ตรวจ metadata วันส่งออกและ `install_year` | ระบุเป็นข้อจำกัดเรื่อง snapshot จำนวนลูกค้า `total customers served` | GIS: จัดเก็บ Snapshot จำนวนผู้ใช้ไฟ ณ สิ้นปี (As-of-Year) |

## 3. สรุปคำที่เขียนต่างกัน (Text & Category Variants)

### `outages_cause`
- **`animal`** ← `Animal`, `งูพันสาย`, `นก/กระรอก`, `สัตว์`
- **`equipment`** ← `Equipment failure`, `ลูกถ้วยแตก`, `หม้อแปลงชำรุด`, `อุปกรณ์ชำรุด`
- **`lightning`** ← `Lightning`, `ฟ้าผ่า`, `ฟ้าผ่าสาย`
- **`overload`** ← `Overload`, `โหลดเกิน`, `ไฟเกิน`
- **`planned`** ← `Planned work`, `ดับไฟตามแผน`, `ปฏิบัติงานตามแผน`
- **`tree`** ← `Tree`, `tree contact`, `กิ่งไม้พาดสาย`, `ต้นไม้`, `ต้นไม้ล้มทับสาย`
- **`unknown`** ← `Unknown`, `ไม่ทราบสาเหตุ`
- **`vehicle`** ← `Vehicle`, `รถชนเสา`

### `outages_type`
- **`Planned`** ← `Planned`, `planned`, `ตามแผน`
- **`Unplanned`** ← `UNPLANNED`, `Unplanned`, `unplanned`, `ไม่ได้วางแผน`

### `feeders_area_type`
- **`Rural`** ← `RURAL`, `Rural`, `rural`, `ชนบท`
- **`Suburban`** ← `Suburban`, `suburban`, `ชานเมือง`
- **`Urban`** ← `Urban`, `urban`

