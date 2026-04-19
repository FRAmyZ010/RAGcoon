import os
import uuid
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http import models
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = os.getenv("COLLECTION_NAME")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")

# 🔥 โหลด model ครั้งเดียว
embedding_model = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)


def upload_to_qdrant(chunks):
    try:
        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        print("🌐 Connected to Qdrant")

        # 🧠 เตรียมข้อมูล
        docs = [c["content"] for c in chunks]
        metas = [c["metadata"] for c in chunks]

        vectors = embedding_model.embed_documents(docs)

        # 📦 สร้าง collection ถ้ายังไม่มี
        collections = [c.name for c in client.get_collections().collections]
        if COLLECTION_NAME not in collections:
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=models.VectorParams(
                    size=len(vectors[0]),
                    distance=models.Distance.COSINE
                )
            )
            print(f"📦 Created collection: {COLLECTION_NAME}")

        # 🚀 Upload (batch)
        batch_size = 50
        for i in range(0, len(vectors), batch_size):
            points = [
                models.PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vectors[j],
                    payload={
                        "content": docs[j],
                        **metas[j]
                    }
                )
                for j in range(i, min(i + batch_size, len(vectors)))
            ]

            client.upsert(collection_name=COLLECTION_NAME, points=points)
            print(f"✅ Uploaded {i + 1} - {i + len(points)}")

        print("✨ Upload complete")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False