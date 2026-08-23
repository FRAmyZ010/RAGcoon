from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import engine, Base, get_db
from app.core.config import settings
import app.models # โหลด Models ทั้งหมด

from app.models.document import Document
from app.schemas.document import ProcessingStatus

# สร้าง Database Table ใน Postgres
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API for RAGcoon Project",
    version="0.1.0"
)

@app.get("/")
def read_root():
    return {"message":f"Welcome to {settings.APP_NAME}"}

@app.get("/health/db")
def health_check_db(db: Session = Depends(get_db)):
    try:
        result = db.execute(text("SELECT 1")).scalar()
        if result == 1:
            return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@app.post("/test/create-doc")
def create_test_document(db: Session = Depends(get_db)):
    # 1. ลองสร้างข้อมูลเอกสารจำลอง
    test_doc = Document(
        filename="test_paper.pdf",
        file_path="/storage/test_paper.pdf",
        title="Sample Research Paper",
        supervisory_committee="Dr. John Doe, Prof. Jane Smith",
        status=ProcessingStatus.PENDING.value
    )
    
    # 2. บันทึกลง PostgreSQL
    db.add(test_doc)
    db.commit()
    db.refresh(test_doc)
    
    return {"message": "Document created successfully!", "document": test_doc}

@app.get("/test/get-docs")
def get_test_documents(db: Session = Depends(get_db)):
    # ดึงข้อมูลทั้งหมดในตาราง documents ออกมาดู
    docs = db.query(Document).all()
    return {"total": len(docs), "documents": docs}