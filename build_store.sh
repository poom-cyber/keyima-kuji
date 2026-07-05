#!/usr/bin/env bash
# ประกอบโฟลเดอร์ store (เว็บร้านสาธารณะ) จากไฟล์ล่าสุดใน site/
# ใช้โดย Netlify build (git deploy) หรือรันเองก่อน CLI deploy ก็ได้
set -e
mkdir -p store
cp site/shop.html  store/index.html
cp site/admin.html store/admin.html
cp site/data.json  store/data.json
echo "built store/ : index.html (shop) + admin.html + data.json"
