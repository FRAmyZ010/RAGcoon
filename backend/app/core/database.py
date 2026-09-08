from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings # import instance from config.py

# สร้าง Engine สำหรับเชื่อมต่อ Postgresql

engine = create_engine(
    settings.get_database_url(),
    pool_pre_ping = True
)

# SessionLocal สำหรับจัดการ Transaction ในแต่ละ Request
SessionLocal = sessionmaker(autocommit = False, autoflush = False, bind = engine)

# Base Class สำหรับทำ Database Models
class Base(DeclarativeBase):
    pass

# Dependency Injection สำหรับดึง DB Session น API Routes
def get_db():
    db = SessionLocal() # Step 1: เปิดสายเชื่อมต่อ DB (สร้าง Session)
    try:
        yield db        # Step 2: ยื่นสาย db นี้ไปให้ API Route เอาไปใช้ แล้ว "หยุดรอ" 
    finally:            # ไม่ว่าจะเกิดอะไรขึ้นก็ตาม finally จะต้องถูกรันเสมอ
        db.close()      # Step 3: พอ API Route ทำงานเสร็จ ไม่ว่าจะเสร็จหรือพัง จะกลับมาสั่งปิดสายที่นี่