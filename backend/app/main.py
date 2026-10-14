from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import engine, Base, get_db, SessionLocal
from app.core.config import settings
import app.models  # โหลด Models ทั้งหมดเพื่อให้ SQLAlchemy สแกน Schema
from app.api.v1.router import api_router
from app.services.auth_service import ensure_administrator_seed

import logging
import time

logger = logging.getLogger("ragcoon.main")

def init_database(max_retries: int = 5, retry_delay: float = 2.0) -> bool:
    """Initialize database tables, run soft migrations, and seed default admin.
    Handles transient DB connection delays (e.g. during Docker container cold start).
    """
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Connecting to database and initializing schema (attempt {attempt}/{max_retries})...")
            Base.metadata.create_all(bind=engine)
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS keywords TEXT"))
            _seed_db = SessionLocal()
            try:
                ensure_administrator_seed(_seed_db)
            finally:
                _seed_db.close()
            logger.info("Database initialized successfully.")
            return True
        except Exception as exc:
            logger.warning(f"Database initialization attempt {attempt} failed: {exc}")
            if attempt < max_retries:
                time.sleep(retry_delay)
            else:
                logger.error("Could not connect to database after retries. Continuing startup.")
                return False

# Attempt immediate initialization (non-blocking if DB not yet reachable)
init_database(max_retries=1, retry_delay=0.5)

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

@app.on_event("startup")
def startup_prewarm():
    """Pre-warm all RAG models and caches asynchronously to eliminate cold-start wait, and ensure DB connection."""
    init_database(max_retries=5, retry_delay=2.0)
    from app.rag.retrieval.prewarm import start_background_prewarm
    start_background_prewarm()

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
