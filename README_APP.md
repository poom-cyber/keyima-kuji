# Kuji Pricer — โครงสร้างระบบ (เวอร์ชันมาตรฐาน)

ระบบเทียบราคา Ichiban Kuji: ราคาขาย Shopee × ต้นทุน Mercari (เยน) → คำนวณมาร์จิน
เปลี่ยนจาก "สคริปต์ + ไฟล์ JSON กระจาย" มาเป็น **ฐานข้อมูล SQLite + REST API (FastAPI) + เว็บแอดมิน**

## โครงสร้างโฟลเดอร์

```
PriceUpdate/
├─ server/              ← Backend (API)
│  ├─ app.py            FastAPI app + ทุก endpoint
│  ├─ db.py             ชั้น SQLite (schema, การเชื่อมต่อ)
│  ├─ migrate.py        นำเข้าไฟล์ JSON เดิม → kuji.db (รันครั้งเดียว/รันซ้ำได้)
│  ├─ export.py         สร้าง site/data.json + site/history.json จาก DB
│  └─ requirements.txt
├─ data/
│  └─ kuji.db           ← ฐานข้อมูลหลัก (source of truth)
├─ web/
│  └─ index.html        ← เว็บแอดมิน (เรียก API: ดูมาร์จิน, แก้ keyword, export)
├─ site/                ← เว็บ static เดิม (data.json/history.json = export จาก DB)
├─ Dockerfile, render.yaml   ← สำหรับ deploy ออนไลน์
├─ start_api.bat        ← ดับเบิลคลิกเพื่อรันบนเครื่อง (Windows)
└─ (ไฟล์ pipeline เดิม: AUTO_TASK.md, merge_shopee.py, db_update.py … ยังใช้ได้)
```

## ฐานข้อมูล (SQLite — `data/kuji.db`)

| ตาราง | เก็บอะไร |
|---|---|
| `collections` | คอลเลคชั่น: id, ชื่อ, รูปปก, jpkw, วันที่ (added/create) |
| `prizes` | รางวัลแต่ละตัว: pz, ราคาขาย Shopee, ต้นทุนเยน (jp), ลิงก์, รูป |
| `keywords` | keyword Mercari ต่อคอล + ธง needs_check |
| `price_history` | ต้นทุนเยนรายวัน (กราฟย้อนหลัง) |
| `meta` | rate (JPY→THB), updated |

> หมายเหตุ: ใน sandbox ของ Claude เขียน SQLite บนโฟลเดอร์ที่ mount ไม่ได้ (disk I/O) จึง build ที่ /tmp แล้วคัดลอกมา — บนเครื่องจริง/เซิร์ฟเวอร์ไม่มีปัญหานี้

## รันบนเครื่อง (Windows)

ดับเบิลคลิก **`start_api.bat`** — จะติดตั้ง dependency, สร้าง DB ถ้ายังไม่มี, เปิดเบราว์เซอร์ที่ http://localhost:8000

หรือสั่งเอง:
```
pip install -r server/requirements.txt
python server/migrate.py            # ครั้งแรก: นำเข้าข้อมูลเดิม
cd server && python -m uvicorn app:app --port 8000
```
- เว็บแอดมิน: http://localhost:8000/
- เอกสาร API (ลองยิงได้): http://localhost:8000/docs

## API หลัก

| Method | Path | ทำอะไร |
|---|---|---|
| GET | `/api/meta` | rate, updated, จำนวนคอล/รางวัล |
| GET | `/api/collections?q=&has_null=` | รายการคอล + รางวัล + มาร์จิน |
| GET | `/api/collections/{id}` | คอลเดียว |
| GET | `/api/margins?threshold=55` | รางวัลมาร์จินต่ำกว่าเกณฑ์ (เรียงบางสุด) |
| GET | `/api/keywords` | แผนที่ keyword + needs_check |
| PUT | `/api/keywords/{id}` | แก้ keyword 1 คอล (sync ลง jpkw ด้วย) |
| POST | `/api/keywords/import` | นำเข้า keyword หลายคอล `{"map":{id:kw}}` |
| GET | `/api/history/{id}` | ประวัติราคาเยน |
| POST | `/api/export` | สร้าง site/data.json + history.json จาก DB |

## Deploy ออนไลน์

**Backend API → Render.com** (มี persistent disk เก็บ SQLite)
1. push โฟลเดอร์นี้ขึ้น GitHub
2. Render → New → Blueprint → เลือก repo (อ่าน `render.yaml` อัตโนมัติ)
3. ได้ URL เช่น `https://kuji-pricer-api.onrender.com`

**Frontend → ใช้ที่ไหนก็ได้:** เปิด web/index.html กดปุ่ม ⚙ ใส่ URL ของ API
หรือเสิร์ฟ web/ จาก API เดียวกันเลย (เปิด `/` ของ API ก็เจอเว็บแอดมิน)

> ทางเลือกอื่น: Railway / Fly.io ก็ใช้ Dockerfile เดียวกันได้

## การเชื่อมกับงานดึงราคา (สำคัญ)

การดึงราคา Mercari **ต้องรันบนเครื่องที่มี Chrome** (ใช้ Claude in Chrome ผ่าน DataDome) — รันบนเซิร์ฟเวอร์ไม่ได้ ดังนั้นโมเดลที่แนะนำ:

1. งานอัตโนมัติรายวัน (ตาม `AUTO_TASK.md`) ดึงราคา → เขียนลง DB ในเครื่อง
2. รัน `python server/export.py` → ได้ site/data.json อัปเดต
3. (ออนไลน์) sync ขึ้น API: เรียก `POST /api/keywords/import` หรือเพิ่ม endpoint อัปราคาในอนาคต / หรือ deploy DB ที่อัปแล้วขึ้นไป

ช่วงเปลี่ยนผ่าน: เว็บ static เดิม + pipeline เดิมยังทำงานได้ปกติ เพราะ `export.py` คง `site/data.json` รูปแบบเดิมไว้ครบ
