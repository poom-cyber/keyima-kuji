# Backend ออนไลน์บน Netlify (Functions + Blobs)

ทำให้ **ออเดอร์ + สต็อก online จริง** (sync ทุกเครื่อง) โดยไม่ต้องมี server แยก — ใช้ **Netlify Functions** (serverless API) + **Netlify Blobs** (ที่เก็บข้อมูลในตัว Netlify, ไม่ต้อง provision, ไม่ใช่ Neon DB ที่กินเครดิต)

> catalog (สินค้า/ราคา) ยังใช้ `data.json` (static บน Netlify CDN — online + ฟรี + เร็ว, บอต Mercari อัปเดตให้) เพราะเป็นข้อมูลอ่านอย่างเดียว ไม่ต้องมี DB สด · ส่วนที่ต้อง DB สดคือ ออเดอร์/สต็อก → เก็บใน Blobs

## ไฟล์ที่เพิ่ม
```
netlify.toml                     ตั้งค่า build/functions
package.json                     dependency @netlify/blobs
build_store.sh                   ประกอบโฟลเดอร์ store จาก site/
netlify/functions/orders.mjs        POST /api/orders (สร้าง) · GET /api/orders (แอดมิน)
netlify/functions/order-status.mjs  PATCH /api/orders/:id (เปลี่ยนสถานะ)
netlify/functions/stock.mjs         GET /api/stock · PATCH /api/stock
```
เก็บใน Blobs 2 store: `orders` (คีย์ = เลขออเดอร์) และ `shop` (คีย์ `stock`)

## Deploy (แนะนำแบบ git — เพราะ Functions เสถียรกว่า)
1. Push โฟลเดอร์ `PriceUpdate` ขึ้น GitHub (ถ้ายังไม่ได้เชื่อม)
2. Netlify → **Add new site → Import from Git** → เลือก repo
   - Netlify จะอ่าน `netlify.toml` เอง (build = `bash build_store.sh`, publish = `store`, functions = `netlify/functions`)
3. ตั้ง **Environment variables** ใน Site settings:
   - `KUJI_ADMIN_TOKEN` = รหัสแอดมิน (เปลี่ยนจาก keyima1234)
   - `KUJI_ORDER_WEBHOOK` = (ไม่บังคับ) URL แจ้งเตือนออเดอร์ใหม่ เข้า Discord/Telegram/Make/Google Apps Script
4. Deploy → ได้โดเมนร้าน เช่น `keyima-store.netlify.app`
   - หน้าร้าน `/` · แอดมิน `/admin.html` · API `/api/orders`, `/api/stock`

**หรือ deploy แบบ CLI** (ไม่ต้อง git): ดับเบิลคลิก `deploy_store.bat` (มี `--functions` แล้ว) — แต่ตั้ง env ต้องทำผ่านหน้า Netlify หรือ `netlify env:set` เอง

## เปิดใช้โหมดออนไลน์ (หลัง deploy Functions สำเร็จ)
แก้ `CONFIG` ทั้งใน `site/shop.html` และ `site/admin.html`:
```js
useBackend: true,     // เดิม false (เดโม) → true
apiBase: "",          // "" = same-origin (Functions อยู่เว็บเดียวกัน) — ถ้า admin คนละโดเมนให้ใส่ URL ร้านเต็ม
```
แล้ว deploy ใหม่ (`deploy_store.bat` หรือ git push) — เสร็จแล้ว:
- ลูกค้าสั่งจากร้าน → `POST /api/orders` → เก็บใน Blobs → **แอดมินเห็นครบทุกเครื่อง**
- แอดมิน toggle สต็อก → `PATCH /api/stock` → ร้านดึง `GET /api/stock` → ขึ้น SOLD OUT
- แอดมินเปลี่ยนสถานะ new→confirmed→paid→shipped → `PATCH /api/orders/:id`

## ทดสอบเร็ว (หลัง deploy)
```
curl https://<ร้าน>.netlify.app/api/stock          # ควรได้ {}
curl -X POST https://<ร้าน>.netlify.app/api/orders -H "content-type: application/json" \
  -d '{"items":[{"cid":"1","pz":"A","qty":1,"price":790,"name":"test"}],"customer":{"name":"x","contact":"line"},"total":790}'
curl https://<ร้าน>.netlify.app/api/orders -H "x-admin-token: <รหัสแอดมิน>"   # เห็นออเดอร์
```

## หมายเหตุ
- **Netlify Blobs** อยู่ในทุกแพลน (เป็น primitive) มีลิมิตการใช้งานตามแพลน — เหมาะกับปริมาณออเดอร์ร้านทั่วไป (ต่างจาก Netlify DB/Neon ที่กินเครดิต)
- catalog อัปเดต: บอต → `db_update.py` → `site/data.json` → deploy (git push / deploy_store.bat) เหมือนเดิม
- ความปลอดภัย: endpoint แอดมิน (GET orders, PATCH) เช็ค `x-admin-token` ฝั่งเซิร์ฟเวอร์ · หน้า `/admin.html` มี token gate (เก็บ URL ไว้เฉพาะ) · เครื่องมือต้นทุน/มาร์จิน (`index.html`) อยู่เว็บส่วนตัวแยก
