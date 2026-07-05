@echo off
REM ===== Deploy เว็บ Kuji ขึ้น Netlify (kuji-price-poom) =====
REM ต้องมี Node.js ติดตั้งในเครื่อง (https://nodejs.org)
cd /d "%~dp0"
set /p TOK=<.netlify_token
echo กำลัง deploy โฟลเดอร์ site ขึ้น Netlify ...
npx -y netlify-cli@latest deploy --dir=site --prod --site 1ed4f760-6ccb-4033-833b-178ff23832d0 --auth %TOK%
echo.
echo เสร็จแล้ว! เปิด https://kuji-price-poom.netlify.app
pause
