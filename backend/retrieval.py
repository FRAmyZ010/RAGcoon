from qdrant_client import QdrantClient
from dotenv import load_dotenv
import os
from sentence_transformers import SentenceTransformer

load_dotenv()

client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY"),
)
print(client.get_collections())

model = SentenceTransformer("intfloat/multilingual-e5-base")

query = "Methology of the Petfeeder project"

query_vector = model.encode([query])[0]

results = client.query_points(
    collection_name="project_documents",  # 👈 ใช้ชื่อที่มีจริง
    query=query_vector,
    limit=3
)

context = [point.payload["text"] for point in results.points]

print(context)