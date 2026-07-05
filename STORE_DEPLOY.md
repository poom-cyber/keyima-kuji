# โครงเว็บ 2 ตัว (แยกสาธารณะ ↔ ส่วนตัว)

แยกเป็น 2 เว็บ Netlify คนละโดเมน เพื่อไม่ให้ลูกค้า/คู่แข่งเห็นต้นทุน–กำไร

| เว็บ | โฟลเดอร์ | เนื้อหา | ใคร | deploy ด้วย |
|---|---|---|---|---|
| **ส่วนตัว (เดิม)** | `site/` | `index.html` เครื่องมือราคา/มาร์จิน + `admin.html` จัดการออเดอร์/สต็อก + data.json | เจ้าของร้านเท่านั้น | `deploy.bat` → kuji-price-poom.netlify.app |
| **สาธารณะ (ใหม่)** | `store/` | `index.html` = หน้าร้าน (Keyima Store) + data.json | ลูกค้า | `deploy_store.bat` → โดเมนใหม่ (เช่น keyima-store.netlify.app) |

> `store/` ถูกสร้าง/อัปเดตอัตโนมัติโดย `deploy_store.bat` (ก๊อป `site/shop.html`→`store/index.html` และ `site/data.json`→`store/data.json`) — ไม่ต้องแก้ในโฟลเดอร์ store เอง แก้ที่ `site/shop.html` ที่เดียว

## ตั้งค่าครั้งแรก (ทำครั้งเดียว)
1. **สร้างเว็บร้านใหม่บน Netlify**
   - `npx -y netlify-cli@latest sites:create --name keyima-store --auth <token ใน .netlify_token>`
   - หรือสร้างในหน้า app.netlify.com → Add new site → copy **Site ID**
2. เปิด `deploy_store.bat` แก้บรรทัด `set STORE_SITE_ID=` ใส่ Site ID ที่ได้
3. ดับเบิลคลิก `deploy_store.bat` → ร้านขึ้นเว็บใหม่

## อัปเดตประจำ
- ราคาต้นทุนเปลี่ยน (หลัง db_update): รัน **`deploy_store.bat`** เพื่ออัป data.json ให้ร้าน (และ `deploy.bat` สำหรับเว็บส่วนตัว)
- แก้หน้าตา/ราคาขายเอง: แก้ `site/shop.html` (บล็อก `CONFIG`) แล้ว `deploy_store.bat`

## เรื่องออเดอร์/สต็อก (สำคัญเมื่อแยก 2 เว็บ)
เพราะร้าน (โดเมน A) กับแอดมิน (โดเมน B) คนละ origin → **localStorage ไม่ sync ข้ามกัน**
- **โหมดเดโม (apiBase ว่าง):** ลูกค้าสั่งจากร้านได้ปกติ (กดทักไลน์ + ก๊อปรายการออเดอร์) แต่ **แดชบอร์ดแอดมินจะไม่เห็นออเดอร์** (เก็บอยู่ในเบราว์เซอร์ลูกค้า)
- **โหมด backend จริง (แนะนำเมื่อแยกเว็บ):** deploy FastAPI (server/) ขึ้น Render แล้วตั้ง `CONFIG.apiBase = "https://<render-url>"` ทั้งใน `site/shop.html` และ `site/admin.html`
  - ออเดอร์จากร้าน → `POST /api/orders` → แอดมินเห็นครบทุกเครื่อง
  - แอดมิน toggle สต็อก → ร้านดึง `GET /api/stock` → ขึ้น SOLD OUT ให้ลูกค้าเห็น
  - ตั้ง env: `KUJI_ADMIN_TOKEN` (รหัสแอดมิน), `KUJI_ORDER_WEBHOOK` (แจ้งเตือนออเดอร์เข้า Discord/Telegram/Make)

## สรุปสั้น
- **1 เว็บใหม่ที่ต้องเพิ่ม** = ร้านสาธารณะ (public) · เว็บส่วนตัวใช้ของเดิม
- ร้านใช้ได้ทันที (สั่งผ่านไลน์) · จะให้แอดมินรวมออเดอร์ข้ามเครื่อง → ต่อ backend (apiBase)
