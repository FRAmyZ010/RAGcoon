import logging
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import engine, Base, get_db
from app.core.config import settings
import app.models  # โหลด Models ทั้งหมดเข้า SQLAlchemy Context

# Import Models & Schemas เพิ่มเติมสำหรับ Test Endpoints
from app.models.document import Document
from app.schemas.document import ProcessingStatus

# Import Routers หลักสำหรับใช้งาน API v1
from app.api.v1.chat import router as chat_router

# ตั้งค่า Logging สำหรับ Backend
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# สร้าง Database Tables ใน PostgreSQL (อ้างอิงจาก SQLAlchemy Models)
Base.metadata.create_all(bind=engine)

# สร้าง FastAPI Application Instance
app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API for RAGcoon Project - Senior Project Document QA System",
    version="0.1.0"
)

# --- Register API Routers ---
app.include_router(chat_router)


# --- System & Health Check Endpoints ---

@app.get("/", tags=["System Check"])
def read_root():
    """
    Root Endpoint สำหรับตรวจสอบสถานะเบื้องต้นของ Backend API
    """
    return {
        "app_name": settings.APP_NAME,
        "status": "running",
        "message": f"Welcome to {settings.APP_NAME} Backend API"
    }


@app.get("/health/db", tags=["System Check"])
def health_check_db(db: Session = Depends(get_db)):
    """
    Health Check Endpoint สำหรับตรวจสอบการเชื่อมต่อกับ PostgreSQL Database
    """
    try:
        result = db.execute(text("SELECT 1")).scalar()
        if result == 1:
            return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        return {"status": "unhealthy", "error": str(e)}


# --- Temporary Test Endpoints (for Data Ingestion / Database Testing) ---

@app.post("/test/create-doc", tags=["Test Endpoints"])
def create_test_document(db: Session = Depends(get_db)):
    """
    Endpoint ทดลองสร้างข้อมูลเอกสารจำลองลง PostgreSQL
    """
    try:
        test_doc = Document(
            filename="test_paper.pdf",
            file_path="/storage/test_paper.pdf",
            title="Sample Research Paper",
            supervisory_committee="Dr. John Doe, Prof. Jane Smith",
            status=ProcessingStatus.PENDING.value
        )
        
        db.add(test_doc)
        db.commit()
        db.refresh(test_doc)
        
        return {
            "message": "Document created successfully!",
            "document": test_doc
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create test document: {str(e)}")
        return {"message": "Failed to create document", "error": str(e)}


@app.get("/test/get-docs", tags=["Test Endpoints"])
def get_test_documents(db: Session = Depends(get_db)):
    """
    Endpoint ดึงรายการเอกสารทั้งหมดในตาราง documents ออกมาตรวจสอบ
    """
    docs = db.query(Document).all()
    return {
        "total": len(docs),
        "documents": docs
    }