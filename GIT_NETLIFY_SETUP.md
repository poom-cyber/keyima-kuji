# เชื่อม GitHub + Netlify (เว็บร้าน + Functions)

ทำครั้งเดียว → หลังจากนั้นแค่ `git push` (หรือดับเบิลคลิก `push_github.bat`) เว็บร้านจะ build/deploy เองอัตโนมัติ

> ทำเฉพาะ **เว็บร้านสาธารณะ** (store + Functions) · เว็บส่วนตัว (เครื่องมือราคา) ใช้ `deploy.bat` เดิมต่อไป ไม่ต้องเชื่อม git

## เตรียมพร้อม (มีแล้วส่วนใหญ่)
- Git ติดตั้งในเครื่อง (ลอง `git --version` ใน cmd) — ไม่มี โหลดที่ https://git-scm.com
- บัญชี GitHub
- `.gitignore` กัน `.netlify_token` ให้แล้ว ✅ (โทเคนไม่หลุดขึ้น GitHub)

---

## ขั้นที่ 1 — สร้าง GitHub repo (ครั้งเดียว)
1. เข้า https://github.com/new
2. ตั้งชื่อ เช่น `keyima-kuji` · เลือก **Private** (แนะนำ) · **อย่า**ติ๊ก Add README
3. กด **Create repository** → ก๊อป URL (เช่น `https://github.com/USERNAME/keyima-kuji.git`)

## ขั้นที่ 2 — ส่งโค้ดขึ้น GitHub
เปิด **Command Prompt** ในโฟลเดอร์ `PriceUpdate` (พิมพ์ `cmd` ในช่อง address ของ File Explorer) แล้ว:
```
git remote add origin https://github.com/USERNAME/keyima-kuji.git
```
จากนั้น **ดับเบิลคลิก `push_github.bat`** (หรือรัน `git add -A && git commit -m "init" && git push -u origin main`)
- ครั้งแรกจะให้ล็อกอิน GitHub (เด้งหน้าเว็บ/ใส่ Personal Access Token) — ทำตามที่มันบอก

## ขั้นที่ 3 — เชื่อม Netlify กับ repo
1. เข้า https://app.netlify.com → **Add new site → Import an existing project**
2. เลือก **GitHub** → authorize → เลือก repo `keyima-kuji`
3. **Build settings** — Netlify อ่านจาก `netlify.toml` ให้เอง:
   - Build command: `bash build_store.sh`
   - Publish directory: `store`
   - Functions directory: `netlify/functions`
   (ถ้ามันไม่ขึ้นให้ ใส่เองตามนี้)
4. กด **Deploy** → รอ build เสร็จ → ได้โดเมน เช่น `keyima-kuji.netlify.app`
   - เปลี่ยนชื่อโดเมนได้ที่ Site configuration → Site name

## ขั้นที่ 4 — ตั้ง Environment variables (ความลับ/แจ้งเตือน)
Site configuration → **Environment variables** → Add:
- `KUJI_ADMIN_TOKEN` = รหัสแอดมินใหม่ (อย่าใช้ keyima1234)
- `KUJI_ORDER_WEBHOOK` = (ไม่บังคับ) URL แจ้งเตือนออเดอร์ใหม่ (Discord/Telegram/Make)
แล้ว Deploys → **Trigger deploy → Clear cache and deploy** ให้ env มีผล

## ขั้นที่ 5 — เปิดโหมดออนไลน์
แก้ `CONFIG` ใน `site/shop.html` และ `site/admin.html`:
```js
useBackend: true,
apiBase: "",
```
ตั้ง `adminToken` ให้ตรงกับ `KUJI_ADMIN_TOKEN` (ใช้ตอนล็อกอินหน้า admin) · ใส่ `lineUrl`/`shopName` ด้วย
แล้ว **`push_github.bat`** อีกครั้ง → Netlify build ใหม่เอง

## เสร็จแล้ว — เช็ก
- ร้าน: `https://<โดเมน>.netlify.app/`
- แอดมิน: `https://<โดเมน>.netlify.app/admin.html` (ล็อกอินด้วย KUJI_ADMIN_TOKEN)
- ทดสอบสั่งจากร้าน → ออเดอร์ต้องโผล่ในแอดมิน (คนละเครื่องก็เห็น) + toggle สต็อก → ร้านขึ้น SOLD OUT

---

## อัปเดตครั้งต่อไป (ประจำ)
- ราคาเปลี่ยน (หลังบอต/`db_update.py`): `push_github.bat` → เว็บร้านอัปเดตเอง
- เว็บส่วนตัว (เครื่องมือราคา): `deploy.bat` เหมือนเดิม

## ปัญหาที่เจอบ่อย
- **push แล้วถาม password/token:** GitHub ยกเลิกรหัสผ่านธรรมดาแล้ว → สร้าง Personal Access Token (github.com → Settings → Developer settings → Tokens) หรือให้ Git Credential Manager เด้งหน้าเว็บให้ล็อกอิน
- **Netlify build fail ที่ build_store.sh:** เช็กว่ามีไฟล์ `site/shop.html`, `site/admin.html`, `site/data.json` ใน repo (push ครบ)
- **/api/orders ได้ 404:** functions ไม่ถูก deploy → เช็ก Functions directory = `netlify/functions` และมี `package.json` (@netlify/blobs) ใน repo
