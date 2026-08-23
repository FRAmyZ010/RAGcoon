from app.core.database import Base
from app.models.document import Document
from app.models.user import User
from app.models.chat import Chat
from app.models.feedback import Feedback

"""
Models Central Package Identifier

ไฟล์นี้ทำหน้าที่รวม ORM Models ทั้งหมดของระบบไว้ที่จุดเดียว:
1. ช่วยให้ SQLAlchemy สแกนเจอทุกตารางเพื่อสร้าง Database Schema อัตโนมัติ
2. ป้องกันปัญหา Circular Import ระหว่าง Models
3. ช่วยให้ไฟล์อื่น Import Class โมเดลไปใช้งานได้สะดวกและสั้นลง
"""

__all__ = ["Base", "Document", "User", "Chat", "Feedback"]