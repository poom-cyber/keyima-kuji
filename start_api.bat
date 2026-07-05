@echo off
REM ===== Kuji Pricer API - รันบนเครื่อง (Windows) =====
REM ดับเบิลคลิกไฟล์นี้เพื่อเปิดเซิร์ฟเวอร์ แล้วเปิดเบราว์เซอร์ที่ http://localhost:8000
cd /d "%~dp0"

REM ติดตั้ง dependency ครั้งแรก (ถ้ายังไม่มี)
python -m pip install -q -r server\requirements.txt

REM ถ้ายังไม่มี DB ให้สร้างจากไฟล์เดิม
if not exist "data\kuji.db" python server\migrate.py

echo.
echo  Kuji Pricer API กำลังรันที่ http://localhost:8000
echo  เว็บแอดมิน: http://localhost:8000/   |   เอกสาร API: http://localhost:8000/docs
echo  (กด Ctrl+C เพื่อหยุด)
echo.
start "" http://localhost:8000/
cd server
python -m uvicorn app:app --host 127.0.0.1 --port 8000
