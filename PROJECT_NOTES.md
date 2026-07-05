# โปรเจกต์: ระบบราคา Kuji (Shopee × Mercari)

ไฟล์นี้คือ "บันทึกโปรเจกต์" ให้แชทไหนของ Claude ก็ทำงานต่อได้ (แม้เปิดแชทใหม่/จากมือถือ)
อ่านไฟล์นี้ก่อนเสมอเมื่อผู้ใช้ขอ "อัปเดตราคา" หรือแก้เว็บ

## ภาพรวม
- ผู้ใช้ขายกล่องสุ่ม Ichiban Kuji บน Shopee (~306 คอลเลคชั่น) พรีจากญี่ปุ่น
- ต้นทุน = ราคา "ซื้อได้เลยที่ถูกสุด" บน Mercari ญี่ปุ่น (ข้ามออคชัน 現在) × เรต JPY→THB
- ต้องเช็กว่ารางวัลไหนมาร์จินบาง (<55%) จะได้ขึ้นราคา

## ไฟล์สำคัญ (ในโฟลเดอร์ PriceUpdate)
- `ราคาShopee_ครบ.html` = แอดมิน (โหลด CSV จาก Shopee, แก้/เลือก/ก๊อป/ดาวน์โหลด data.json)
- `site/index.html` = เว็บออนไลน์ (ดึง data.json มาแสดง + เลือก/ก๊อป/ปรับราคา/วางราคา)
- `site/data.json` = ข้อมูลที่เว็บออนไลน์ใช้ {rate, updated, collections:[{id,name,cover,prizes:[{pz,shopee,img,jp,jpkw?}]}]}
- `keywords.json` = แผนที่คีย์เวิร์ด Mercari ต่อคอล (id -> ชื่อชุดญี่ปุ่นเฉพาะ) — เพิ่มเรื่อยๆ จนครบ
- `deploy.bat` = ดับเบิลคลิกบนเครื่องผู้ใช้เพื่อ deploy โฟลเดอร์ site ขึ้น Netlify (ต้องมี Node.js)
- `.netlify_token` = Netlify personal access token (อย่า commit/อย่าเอาเข้าโฟลเดอร์ site!)
- แหล่ง CSV ดิบจาก Shopee: ไฟล์ที่ผู้ใช้อัปโหลด `product list.csv` (ราคา/ตัวเลือก) + `photo_product_list.csv` (รูป)

## Netlify
- site name: kuji-price-poom
- siteId: 1ed4f760-6ccb-4033-833b-178ff23832d0
- URL: https://kuji-price-poom.netlify.app
- deploy: รัน deploy.bat บนเครื่องผู้ใช้ (sandbox ของ Claude ต่อ Netlify ไม่ได้)

## ขั้นตอน "อัปเดตราคา" (ทำเมื่อผู้ใช้ขอ)
1. รับรายการคอลที่จะอัปเดต (ผู้ใช้ก๊อปจากเว็บ/แอดมิน มาวาง: มี id + รางวัล + keyword)
2. หา keyword เฉพาะชุดจาก keywords.json (ถ้าไม่มี ให้หาเพิ่มแล้วบันทึกลง keywords.json)
3. ดึง Mercari ด้วย mcp__workspace__web_fetch (URL: https://jp.mercari.com/search?keyword=<urlencoded>) — ถ้า URL ใหม่ติด provenance ให้ใช้ WebSearch (allowed_domains jp.mercari.com) ก่อนเพื่อให้ URL เข้า provenance
4. หาราคา "ซื้อได้เลยถูกสุด" ต่อรางวัล (ข้าม 現在 = ออคชัน, ข้ามรายการที่จองชื่อ '...様', ข้ามเซ็ตรวม) จับคู่ด้วยตัวอักษรรางวัล A/B/C/ラストワン
5. เขียนต้นทุน (เยน) ลง site/data.json ในฟิลด์ prizes[].jp ของ id นั้น (จับคู่ด้วยชื่อ pz)
6. อัปเดต data.json.updated = วันที่วันนี้
7. แจ้งผู้ใช้ให้ดับเบิลคลิก deploy.bat (หรือผู้ใช้ลากโฟลเดอร์ site ขึ้น Netlify) เพื่อเผยแพร่
   - และส่ง "บล็อก JSON" ให้ผู้ใช้ด้วย เผื่ออยากกด 📥 วางราคา บนเว็บ/แอดมินเอง
   - รูปแบบบล็อก: { "<id>": { "<ชื่อรางวัล>": <เยน>, ... }, ... }

## เรต JPY→THB
- ดึงล่าสุดด้วย WebSearch ก่อนคำนวณ; ถ้าไม่ได้ใช้ 0.206

## ข้อจำกัดที่รู้แล้ว
- เว็บ static ดึง Mercari เองไม่ได้ — Claude เป็นคนดึง
- Claude sandbox ต่อ Netlify ไม่ได้ — deploy ต้องทำบนเครื่องผู้ใช้ (deploy.bat)
- ทำ 306 คอลในรันเดียวไม่ไหว — แบ่งล็อต (~40-50/วัน) และต้องมี keyword ก่อนถึงจะแม่น


## ➕ เพิ่มคอลเลคชั่นใหม่ (เมื่อมีสินค้าใหม่บน Shopee)
**อย่า** โหลด CSV ในหน้าแอดมินแล้วกดดาวน์โหลด data.json ทับ — จะทับต้นทุน jp/jpkw/jpDate/ประวัติ ที่บอทดึงมาหาย
(แอดมินเก็บ jp ใน localStorage เบราว์เซอร์ ไม่ใช่ตัวที่บอทเขียนใน site/data.json)

วิธีปลอดภัย (ผู้ใช้ส่ง CSV 2 ไฟล์จาก Shopee ให้ Claude หรือรันเอง):
1. Export จาก Shopee: `product list.csv` (variation_price) + `photo_product_list.csv` (cover_image)
2. รัน `python3 merge_shopee.py "product list.csv" "photo_product_list.csv"`
   - เพิ่มคอลใหม่ (jp=null), เพิ่มรางวัลใหม่, อัปเดตชื่อ/รูป/ราคาขาย Shopee
   - เก็บต้นทุน jp/jpkw/jpDate/ประวัติ ของคอลเดิมไว้ครบ
3. รัน `python3 db_update.py` (เติม jpkw/jpUrl/jpDate + ประวัติ ให้คอลใหม่)
4. ดับเบิลคลิก `deploy.bat`
5. คอลใหม่จะขึ้น "⚪ ยังไม่อัป" (sort เลือก "ยังไม่อัป/เก่าสุดก่อน" เพื่อไล่เก็บ) — รอบอัตโนมัติประจำวันจะดึง Mercari ให้เองตาม rotation
   หรือสั่งอัปเดตเฉพาะคอลใหม่ทันทีก็ได้ (ก๊อปคำขอจากเว็บ → วางในแชท)
