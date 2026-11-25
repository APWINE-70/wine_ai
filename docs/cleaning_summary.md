# สรุปผลการทำความสะอาดข้อมูล: ค่าผิดปกติและค่าเกินจริง (`wine_ai`)

> **แหล่งอ้างอิง:** [docs/problem_analysis.md](problem_analysis.md) · [docs/quality_report.md](quality_report.md) · [src/pipeline.py](../src/pipeline.py) · [src/metrics.py](../src/metrics.py) · [data/clean/audit_log.json](../data/clean/audit_log.json)  
> **ขอบเขตข้อมูล:** 1 ม.ค. 2566 – 31 ธ.ค. 2567 (`2023-01-01` ถึง `2024-12-31 23:59`) · **การรันซ้ำ:** Deterministic 100% (ไม่แก้ไฟล์ต้นฉบับใน `data/raw/`)

---

## 1. ภาพรวมจำนวนแถวก่อน–หลังทำความสะอาด (Row Accounting)

| ตาราง | แถวดิบ | แถวหลัง Clean | แถวที่ตัด/รวมซ้ำ | เหตุผลที่นับได้ 100% (Zero Silent Drops) |
|---|---:|---:|---:|---|
| **`outages`** | 2,843 | **2,743** *(Unplanned 2,594 · Planned 149)* | -100 | ลบแถวซ้ำทุกคอลัมน์ **68** แถว + ลบแถวซ้ำข้ามช่องทาง (`feeder_id + start_time`) **32** แถว (`strict_valid_rows = 2,664`) |
| **`feeders`** | 55 | **54** | -1 | ลบแถวซ้ำของสายป้อน `CMI-F18` **1** แถว |
| **`substations`** | 8 | **8** | 0 | Flatten โครงสร้าง `location.province` / `location.region` และแปลง `"75 MVA"` → `75.0` |
| **`weather_daily`** | 2,899 | **2,899** | 0 | ยังมี **25** province-days ที่ขาดจากปฏิทินเต็ม 2,924 แถว (คงไว้ด้วย Left Join) |

---

## 2. สรุปการคลีน "ค่าผิดปกติ" และ "ค่าเกินจริง" แยกตามประเภท

### 2.1 ค่าเกินจริง / ค่าหลอก / ผิดหน่วย (Exaggerated & Unit Errors)

| ตาราง / คอลัมน์ | ปัญหาที่พบ | จำนวน | ช่วงค่าก่อนแก้ | วิธีแก้ใน Pipeline | ช่วงค่าหลังแก้ |
|---|---|---:|---|---|---|
| `outages.duration_min` | ค่า placeholder เกินจริง (`9999`, `99999`, `14400`) | **8 แถว** | `9,999 – 99,999` นาที | ล้างเป็น `NaN` (ใน `strict_clean`) และคำนวณค่าสำรอง `duration_min_imputed` จากมัธยฐานกลุ่ม `(area_type, cause)` | `2.0 – 4,159.0` นาที (มัธยฐาน `110.0`) |
| `outages.duration_min` | บันทึกเป็น **ชั่วโมง** แทนนาที (`dur * 60 ≈ end - start`) | **41 แถว** | `0.2 – 6.x` (ไม่ตรง timestamp) | แทนที่ด้วย `(end_time - start_time)` หน่วยนาที | ตรงตาม timestamp 100% |
| `outages.customers_affected` | จำนวนผู้ถูกไฟดับ **เกินผู้ใช้ไฟทั้งสายป้อน** (`> feeder.Customers`) | **16 แถว** | สูงสุด **`29,178`** ราย (เกินจริง 2–10 เท่า) | เก็บค่าดิบใน `customers_affected_raw`, ค่า cap ที่ 100% ใน `customers_affected_capped`, และแทนที่ด้วยมัธยฐานปกติของสายป้อน/ประเภทเหตุการณ์ใน `customers_affected` | `2 – 7,593` ราย (มัธยฐาน `885.0`) |
| `feeders.Length` | บันทึกเป็น **เมตร** แทนกิโลเมตร (`> 1000`) | **4 แถว** | `5.0 – 76,900.0` | หารด้วย `1,000` สำหรับสายที่ `length > 1000` (`CMI-F07`, `CMI-F19`, `LPG-F04`, `LPG-F09`) | `5.0 – 84.8` กม. |
| `weather.max_temp_c` | อุณหภูมิ จ.ลำพูน (มิ.ย.–ก.ค. 2566) เป็น **°F** (`> 50`) | **60 แถว** | `84.0 – 95.5` | แปลงเป็น °C ด้วยสูตร `(°F − 32) × 5/9` | `24.4 – 40.5` °C |
| `weather.rainfall_mm` | ค่า sentinel error `-999.0` | **40 แถว** | `-999.0 – 186.4` | แปลง `-999` เป็น `NaN` เพื่อไม่ให้บิดเบือนค่าเฉลี่ยและค่าสหสัมพันธ์ | `0.0 – 186.4` มม. |

### 2.2 ค่าผิดปกติเชิงเวลา โครงสร้าง และข้อมูลขาดหาย (Temporal, Structural & Missing Anomalies)

| ตาราง / คอลัมน์ | ปัญหาที่พบ | จำนวน | วิธีแก้ใน Pipeline |
|---|---|---:|---|
| `outages.start_time` / `end_time` | วันที่ พ.ศ. รูปแบบ `dd/mm/YYYY` (2566/2567) | **250 เหตุการณ์** *(254 start / 246 end ดิบ)* | Parse แบบ day-first และลบ `543` ออกจากปี `>= 2400` |
| `outages.start_time` | ปีพิมพ์ผิดอยู่นอกช่วง (`2014`, `2042`, `2204`) | **5 แถว** | กู้ปีที่ถูกต้องจาก `outage_id` (`OUT-2023-...`/`OUT-2024-...`) และ `end_time` |
| `outages.start_time` / `end_time` | เวลาเริ่ม–สิ้นสุดสลับกัน (`end < start` ทำให้ duration ติดลบ) | **13 แถว** *(หลังลบซ้ำ)* | สลับ `start_time` ↔ `end_time` และคำนวณ duration เป็นบวก (`-1,375` → `+1,375`) |
| `outages.duration_min` / `end_time` | `duration_min` ว่าง (107 แถวกู้ได้) / `end_time` ว่าง (79 แถวกู้ได้) / ว่างทั้งคู่ (3 แถว) | **107 + 79 + 3** | คำนวณคืนจากคู่ timestamp/duration ที่สมบูรณ์ และแยก 3 แถวที่ว่างทั้งคู่ไว้ทำ dual reporting |
| `outages.crew_arrival_min` | ค่าติดลบ (`-54` ถึง `-14`) | **8 แถว** | ล้างเป็น `NaN` (`5.0 – 228.0` นาที, มัธยฐาน `41.0`) · **หมายเหตุ:** กรณี `crew_arrival_min > duration_min` (405 เหตุการณ์) เป็นเหตุการณ์จริงเมื่อ SCADA กู้ไฟคืนก่อนทีมช่างถึงหน้างาน จึงคงไว้ตามเดิม |
| `outages.feeder_id` | รูปแบบไม่มาตรฐาน (ตัวพิมพ์เล็ก/ไม่มีขีด/ไม่เติม `0`) และรหัสกำพร้า (orphan) | **108 format + 10 orphan** | Normalize เป็น `XXX-FNN` (FK match **99.64%**), คง 10 แถว orphan ไว้พร้อม flag `is_orphan_feeder` |
| `outages.cause` / `outage_type` | คำเรียก 26 แบบ + ค่าว่าง `74` แถว / `outage_type` 7 แบบ | **ทุกแถว** | รวมเป็น `cause` มาตรฐาน 8 กลุ่ม และ `outage_type` 2 กลุ่ม (`Unplanned` / `Planned`) |
| `outages.customers_affected` | รูปแบบข้อความมีจุลภาค (`"1,250"`) และค่าว่าง (`NA`/`-`/`ไม่ระบุ`) | **149 comma + 68 missing** | ลบจุลภาคและทำ `customers_affected_imputed` (มัธยฐานกลุ่ม) ควบคู่ `strict_clean` |
| `feeders.Customers` | ค่าว่างใน `CMI-F02` และ `LPG-F12` | **2 แถว** | ประมาณด้วยมัธยฐาน `area_type` ทำให้ตัวหารรวมเป็น `214,266` ราย (เทียบกับ raw non-null `204,615` ราย) |
| `outages` (พายุจริง vs Error) | เหตุการณ์รุนแรงจริง (`> Q3 + 3×IQR = 664` นาที) และ **พายุเชียงราย 22–23 ส.ค. 2567** | **61 extreme** *(82 เหตุการณ์ใน 2 วันพายุ)* | **ห้ามลบทิ้ง** — คงไว้ในชุด clean และรายงานแยกแบบ **รวมพายุ vs ไม่รวมพายุ** |

---

## 3. ผลกระทบเชิงตัวเลขต่อ SAIFI / SAIDI / CAIDI (Before vs After Cleaning)

คำนวณเฉพาะเหตุการณ์ **Unplanned** (ตัด `Planned` ออก **149** เหตุการณ์: ปี 2566 = 65 ครั้ง, ปี 2567 = 84 ครั้ง)

| กรณีการคำนวณ | ปี 2566 (2023) | ปี 2567 (2024) | เปลี่ยนแปลง YoY | ข้อสังเกตสำคัญ |
|---|---:|---:|---:|---|
| **1. ข้อมูลดิบก่อนคลีน (`raw_uncleaned`)** | 1,180 ครั้ง<br>SAIFI **6.93**<br>SAIDI **2,898.54** นาที<br>CAIDI **418.38** นาที | 1,414 ครั้ง<br>SAIFI **8.33**<br>SAIDI **2,232.83** นาที<br>CAIDI **268.10** นาที | SAIDI **-22.97%** | **หลอกตา!** ค่า `99999` และ `customers_affected` เกินจริงทำให้ SAIDI ปี 2566 พุ่งเกินจริง >3.5 เท่า จนสรุปผิดว่าปี 2567 ดีขึ้น |
| **2. หลังคลีน + Impute ครบทุกเหตุการณ์ (`clean_imputed_all_unplanned`)** | 1,180 ครั้ง<br>SAIFI **6.32**<br>SAIDI **817.01** นาที<br>CAIDI **129.31** นาที | 1,414 ครั้ง<br>SAIFI **7.65**<br>SAIDI **1,155.79** นาที<br>CAIDI **151.06** นาที | ครั้ง **+19.83%**<br>SAIFI **+21.10%**<br>SAIDI **+41.47%** | ตัวเลขจริงสะท้อนว่าความน่าเชื่อถือปี 2567 **แย่ลงอย่างมีนัยสำคัญ** |
| **3. หลังคลีนแบบไม่ Impute ค่าว่าง (`strict_clean`)** | 1,145 ครั้ง<br>SAIFI **6.14**<br>SAIDI **795.21** นาที<br>CAIDI **129.49** นาที | 1,375 ครั้ง<br>SAIFI **7.44**<br>SAIDI **1,119.95** นาที<br>CAIDI **150.43** นาที | ครั้ง **+20.09%**<br>SAIFI **+21.23%**<br>SAIDI **+40.84%** | Sensitivity ของการตัดแถวค่า impact ที่ขาด (~2.7–3.1% ของ SAIDI) |
| **4. หลังคลีน ไม่รวมพายุเชียงราย 22–23 ส.ค. 2567** | 1,180 ครั้ง<br>SAIFI **6.32**<br>SAIDI **817.01** นาที | 1,332 ครั้ง<br>SAIFI **7.29**<br>SAIDI **895.30** นาที | ครั้ง **+12.88%**<br>SAIFI **+15.43%**<br>SAIDI **+9.58%** | แยกให้เห็นว่าพายุ 2 วันในเชียงราย (82 เหตุการณ์) อธิบาย ~260.5 นาทีของ SAIDI ปี 2567 |

---

## 4. สถิติสำคัญหลังทำความสะอาด (พร้อมใช้งานต่อใน Mission B & C)

- **Top 5 สายป้อนที่สร้าง customer-minutes สูงสุด (ไม่รวม 10 แถว orphan):**
  1. `CRI-F11` (เชียงราย · Rural): 155 ครั้ง · 39,411,384 customer-minutes
  2. `CRI-F03` (เชียงราย · Rural): 103 ครั้ง · 26,613,531 customer-minutes
  3. `CRI-F04` (เชียงราย · Rural): 114 ครั้ง · 24,247,519 customer-minutes
  4. `LPG-F09` (ลำปาง · Rural): 135 ครั้ง · 23,832,468 customer-minutes
  5. `CRI-F13` (เชียงราย · Rural): 118 ครั้ง · 23,019,863 customer-minutes
- **Top สาเหตุ (Unplanned):**
  - `tree`: 1,121 ครั้ง (**43.2%** ของครั้ง) แต่กิน **235,523,192.5** customer-minutes (**55.7%** ของผลกระทบ)
  - `equipment`: 283 ครั้ง · **70,367,796.0** customer-minutes (**16.6%**)
  - `animal`: 538 ครั้ง (**20.7%** ของครั้ง) แต่กินเพียง **23,697,356.0** customer-minutes (**5.6%**)

---

## 5. ไฟล์ผลลัพธ์ที่สร้างขึ้นใน Workspace (`C:\Apai`)

- **ข้อมูลหลังทำความสะอาด:** `data/clean/outages_clean.{parquet,csv}`, `data/clean/outages_enriched.{parquet,csv}`, `data/clean/feeders_clean.{parquet,csv}`, `data/clean/substations_clean.{parquet,csv}`, `data/clean/weather_clean.{parquet,csv}`
- **ไฟล์ตรวจสอบและสรุป:** [data/clean/audit_log.json](../data/clean/audit_log.json), [data/clean/quality_audit_summary.json](../data/clean/quality_audit_summary.json), [data/clean/dashboard_bundle.json](../data/clean/dashboard_bundle.json)
- **รายงานเอกสาร:** [docs/quality_report.md](quality_report.md) และ [docs/cleaning_summary.md](cleaning_summary.md)
- **คำสั่งรันซ้ำและทดสอบ:**
  ```powershell
  python -m src.audit_quality
  python -m src.pipeline
  python -m src.metrics
  python -m unittest discover -s tests -v
  ```
