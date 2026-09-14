from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import engine, Base, get_db
from app.core.config import settings
import app.models  # โหลด Models ทั้งหมดเพื่อให้ SQLAlchemy สแกน Schema
from app.api.v1.router import api_router

# สร้างตารางใน PostgreSQL หากยังไม่มี
Base.metadata.create_all(bind=engine)

# Soft-migrate: เพิ่มคอลัมน์ใหม่บน DB ที่มีอยู่แล้ว (create_all ไม่แก้ตารางเก่า)
with engine.begin() as conn:
    conn.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS keywords TEXT"))

app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API for RAGcoon Senior Project Management System",
    version="0.1.0"
)

# ตั้งค่า CORS สำหรับเชื่อมต่อกับ Frontend (React)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ลงทะเบียน Central Router (/api/v1)
app.include_router(api_router)

@app.get("/", tags=["System"])
def root():
    return {"message": f"Welcome to {settings.APP_NAME} API"}

@app.get("/health/db", tags=["System"])
def health_check_db(db: Session = Depends(get_db)):
    try:
        result = db.execute(text("SELECT 1")).scalar()
        if result == 1:
            return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

# --- Temporary Test Endpoints (for Data Ingestion / Database Testing) ---
