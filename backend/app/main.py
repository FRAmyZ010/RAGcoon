from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import engine, Base, get_db
from app.core.config import settings

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

