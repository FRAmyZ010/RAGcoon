FROM python:3.11-slim

# ตั้งค่า Environment variables เพื่อป้องกันไม่ให้ Python สร้าง .pyc และบังคับให้ output ออกทันที
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# ติดตั้ง system dependencies ที่จำเป็นสำหรับ pdfplumber และ psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements และทำการ install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code ทั้งหมดเข้า container
COPY . .

# สั่งรัน FastAPI ด้วย Uvicorn โดยตรง
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]