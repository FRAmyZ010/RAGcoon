import os
from dotenv import load_dotenv

# โหลดค่าจากไฟล์ .env
load_dotenv()

class Config:
    QDRANT_URL = os.getenv("QDRANT_URL")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
    COLLECTION_NAME = os.getenv("COLLECTION_NAME")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")

    @classmethod
    def validate(cls):
        """เช็คว่าค่าที่จำเป็นถูกโหลดมาครบไหม"""
        missing = [k for k, v in cls.__dict__.items() if not k.startswith("__") and v is None]
        if missing:
            raise ValueError(f"⚠️ Missing environment variables: {', '.join(missing)}")