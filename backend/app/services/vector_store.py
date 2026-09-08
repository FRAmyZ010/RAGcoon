from qdrant_client import QdrantClient
from qdrant_client.http import models
from app.core.config import settings

"""
Qdrant Vector Store Service Layer

ไฟล์นี้ทำหน้าที่เป็น Interface หลักในการจัดการ Qdrant Cloud Database:
1. เชื่อมต่อกับ Qdrant Cluster ผ่าน API Key และ URL
2. ตรวจสอบและสร้าง Collection สำหรับเก็บ Vector Embeddings พร้อมกำหนดค่า Cosine Distance และ Vector Dimension (768)
3. ให้บริการ Instance สำเร็จรูป (vector_store_service) สำหรับนำไปใช้ต่อใน RAG Ingestion Pipeline
"""

class VectorStoreService:

    # Qdrant Connection
    def __init__(self):
        self.client = QdrantClient(
            url = settings.QDRANT_URL,
            api_key = settings.QDRANT_API_KEY,
        )

    # Checking and Create Collection
    def create_collection_if_not_exists(self, collection_name:str, vector_size: int = 768):
        collections = self.client.get_collections().collections
        exists = any(c.name == collection_name for c in collections)

        if not exists:
            self.client.create_collection(
                collection_name = collection_name,
                vectors_config=models.VectorParams(
                    size = vector_size,
                    distance = models.Distance.COSINE
                )
            )

# สร้าง Object สำเร็จรูป เพื่อให้ Service หรือ Endpoint อื่นๆ สามารถเรียกใช้งานต่อได้ทันทีโดยไม่ต้องสั่งเปิด Connection ใหม่ทุกรอบ
vector_store_service = VectorStoreService()