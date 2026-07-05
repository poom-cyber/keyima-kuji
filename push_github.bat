@echo off
REM ===== ส่งโค้ดขึ้น GitHub (สำหรับให้ Netlify build เว็บร้าน + Functions) =====
cd /d "%~dp0"

REM ---- init git repo ถ้ายังไม่มี ----
if not exist ".git" (
  echo [..] สร้าง git repo ...
  git init
  git branch -M main
)

REM ---- เช็กว่าผูก GitHub repo แล้วหรือยัง ----
git remote get-url origin >nul 2>&1
if errorlevel 1 (
  echo.
  echo ========== ยังไม่ได้ผูก GitHub repo ==========
  echo 1^) สร้าง repo เปล่าที่ https://github.com/new  ^(ไม่ต้องติ๊ก README^)
  echo 2^) ก๊อป URL แล้วรันครั้งเดียว ^(แก้ USERNAME/REPO^):
  echo        git remote add origin https://github.com/USERNAME/REPO.git
  echo 3^) รัน push_github.bat นี้อีกครั้ง
  echo =============================================
  pause
  exit /b
)

echo กำลังส่งขึ้น GitHub ...
git add -A
git commit -m "update: store + netlify functions"
git branch -M main
git push -u origin main
echo.
echo เสร็จ! ไปเชื่อม Netlify ต่อได้เลย (ดู GIT_NETLIFY_SETUP.md)
pause
