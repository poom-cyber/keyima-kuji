@echo off
REM ============================================================
REM  Deploy "หน้าร้านลูกค้า" (Keyima Store) ขึ้น Netlify เว็บสาธารณะ
REM  *** คนละเว็บ/โดเมน กับ site เดิม (เครื่องมือราคา+แอดมิน = ส่วนตัว) ***
REM  ต้องมี Node.js (https://nodejs.org)
REM ============================================================
cd /d "%~dp0"

REM ---- 1) เตรียมโฟลเดอร์ store = หน้าร้าน (index.html) + ข้อมูลสินค้า (data.json) ----
if not exist store mkdir store
copy /Y site\shop.html  store\index.html >nul
copy /Y site\admin.html store\admin.html >nul
copy /Y site\data.json  store\data.json  >nul
echo [ok] เตรียมไฟล์ร้าน (store\index.html + admin.html + data.json) จากไฟล์ล่าสุดแล้ว

REM ---- ติดตั้ง dependency ของ functions (@netlify/blobs) ครั้งแรก ----
if not exist node_modules (
  echo [..] ติดตั้ง dependency ของ functions ครั้งแรก ^(รอสักครู่^) ...
  call npm install --silent
)

REM ---- 2) ใส่ Site ID ของ "เว็บร้านใหม่" (สร้างครั้งเดียว ดูวิธีด้านล่าง) ----
set STORE_SITE_ID=

set /p TOK=<.netlify_token

if "%STORE_SITE_ID%"=="" (
  echo.
  echo ================= ยังไม่ได้ตั้ง STORE_SITE_ID =================
  echo สร้างเว็บร้านสาธารณะใหม่ครั้งเดียวก่อน แล้วเอา Site ID มาใส่:
  echo.
  echo   วิธี A ^(command^):
  echo     npx -y netlify-cli@latest sites:create --name keyima-store --auth %TOK%
  echo.
  echo   วิธี B ^(หน้าเว็บ^): เข้า app.netlify.com ^> Add new site ^> ตั้งชื่อ
  echo     แล้ว copy "Site ID" จาก Site configuration
  echo.
  echo จากนั้นแก้บรรทัดในไฟล์นี้:  set STORE_SITE_ID=^<ใส่ Site ID^>
  echo แล้วดับเบิลคลิก deploy_store.bat อีกครั้ง
  echo =============================================================
  pause
  exit /b
)

echo กำลัง deploy โฟลเดอร์ store + Functions ขึ้น Netlify (ร้านสาธารณะ) ...
npx -y netlify-cli@latest deploy --dir=store --functions=netlify\functions --prod --site %STORE_SITE_ID% --auth %TOK%
echo.
echo เสร็จแล้ว! เปิดเว็บร้านของคุณได้เลย
echo (ทุกครั้งที่ราคาอัปเดต ให้รัน deploy_store.bat ซ้ำ เพื่ออัป data.json ให้ร้าน)
pause
