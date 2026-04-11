from qdrant_client import QdrantClient
from qdrant_client.http import models

class QdrantManager:
    def __init__(self, url, api_key):
        self.client = QdrantClient(url=url, api_key=api_key)

    def store_vectors(self, collection_name, points):
        if not self.client.collection_exists(collection_name=collection_name):
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=len(points[0].vector),
                    distance=models.Distance.COSINE
                ),
            )
        self.client.upsert(collection_name=collection_name, points=points)