# ใช้ Python 3.11 slim image เพื่อขนาดที่เบาและรวดเร็ว
FROM python:3.11-slim

# ตั้งค่า Environment variables สำหรับ Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

# ติดตั้ง System dependencies ที่จำเป็นสำหรับ PostgreSQL และ PDF parsing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# กำหนด Working directory
WORKDIR /app

# คัดลอกไฟล์ requirements.txt
COPY requirements.txt ./

# ติดตั้ง Python Packages
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# คัดลอก Source Code ทั้งหมด
COPY . .

# เปิด Port 8000 สำหรับ FastAPI
EXPOSE 8000

# คำสั่งสำหรับเริ่มรัน FastAPI ด้วย Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]