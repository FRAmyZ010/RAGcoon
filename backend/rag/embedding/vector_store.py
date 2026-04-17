import uuid
from qdrant_client import QdrantClient
from qdrant_client.http import models
from langchain_huggingface import HuggingFaceEmbeddings

import os
from dotenv import load_dotenv

def upload_to_qdrant(chunks):
    

    QDRANT_URL = os.getenv("QDRANT_URL")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
    COLLECTION_NAME = os.getenv("COLLECTION_NAME")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")
    
    # 1. สร้าง Client และตรวจสอบการเชื่อมต่อ (Health Check)
    try:
        client = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
            check_compatibility=False,
            timeout=60  # เพิ่ม Timeout เป็น 60 วินาที
        )
        # ตรวจสอบว่าเชื่อมต่อได้จริงไหม
        collections = client.get_collections()
        print("🌐 Connection to Qdrant Cloud: OK")
    except Exception as e:
        print(f"❌ Connection Failed: ไม่สามารถติดต่อ Qdrant Cloud ได้ ({e})")
        return False

    # 2. เตรียม Embedding Model
    print("🧠 Initializing Embedding Model...")
    embeddings_model = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    # 3. เตรียมข้อมูล
    documents = [c['content'] for c in chunks]
    metadatas = [c['metadata'] for c in chunks]

    # 4. แปลงเป็น Vectors (ทำทั้งหมดทีเดียวได้ เพราะรันในเครื่องเรา)
    print(f"🧠 Generating {len(documents)} Embeddings...")
    vectors = embeddings_model.embed_documents(documents)

    # 5. แบ่งข้อมูลเป็น Batch เพื่อส่ง (ป้องกัน Server Disconnect)
    batch_size = 20  # ส่งทีละ 20 จุด
    total_chunks = len(vectors)
    print(f"🚀 Pushing to Qdrant Cloud (Batch size: {batch_size})...")

    try:
        for i in range(0, total_chunks, batch_size):
            batch_end = min(i + batch_size, total_chunks)
            
            points = [
                models.PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vectors[j],
                    payload={
                        "page_content": documents[j],
                        "metadata": metadatas[j]
                    }
                )
                for j in range(i, batch_end)
            ]

            client.upsert(
                collection_name=COLLECTION_NAME,
                points=points
            )
            print(f"✅ Uploaded chunks {i+1} to {batch_end}...")

        print("✨ All data uploaded successfully!")
        return True

    except Exception as e:
        print(f"❌ Upload Error during batch processing: {e}")
        return False