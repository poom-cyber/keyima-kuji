# Kuji Pricer API — container สำหรับ deploy ออนไลน์
FROM python:3.11-slim

WORKDIR /app
COPY server/requirements.txt server/requirements.txt
RUN pip install --no-cache-dir -r server/requirements.txt

# โค้ด + ข้อมูลเริ่มต้น
COPY server/ server/
COPY web/ web/
COPY data/ data/
COPY site/ site/

# DB อยู่บน persistent volume (ตั้ง env KUJI_DB ให้ชี้ไป volume ตอน deploy)
ENV KUJI_DB=/var/data/kuji.db
ENV KUJI_CORS=*
EXPOSE 8000

# ถ้า volume ยังว่าง ให้ก๊อป DB เริ่มต้นเข้าไปครั้งแรก แล้วค่อยสตาร์ท
CMD ["sh","-c","mkdir -p /var/data && [ -f \"$KUJI_DB\" ] || cp data/kuji.db \"$KUJI_DB\"; cd server && python -m uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]
