# 1. ใช้ Python 3.11 Slim Image
FROM python:3.11-slim

# 2. ตั้งค่า Environment Variables สำหรับ Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 3. กำหนด Work Directory
WORKDIR /app

# 4. ติดตั้ง System Dependencies ที่จำเป็น
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 5. ติดตั้ง Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 6. คัดลอก Source Code ทั้งหมด
COPY . .

# 7. แปลงไฟล์ entrypoint.sh ให้สามารถ Execute ได้
RUN chmod +x ./scripts/entrypoint.sh

# 8. Expose Port 8000
EXPOSE 8000

# 9. คำสั่งเริ่มต้น Container
ENTRYPOINT ["./scripts/entrypoint.sh"]