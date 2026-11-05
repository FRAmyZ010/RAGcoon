import os
import uuid
from pathlib import Path
from typing import Any, Iterable, Mapping

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http import models
from .embeddings import get_shared_embedding_model

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "embedding_evaluation")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-base")
FILTERABLE_FIELDS = (
    "project_title",
    "author",
    "advisor",
    "committee",
    "year",
    "school",
    "program",
    "project_type",
    "key_technologies",
    "source",
)


def get_embedding_model():
    """Load the embedding model only when an upload is requested."""
    return get_shared_embedding_model(EMBEDDING_MODEL)


def ensure_payload_indexes(client: QdrantClient) -> None:
    """Create keyword indexes required for Qdrant metadata filtering."""
    for field_name in FILTERABLE_FIELDS:
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name=field_name,
            field_schema=models.PayloadSchemaType.KEYWORD,
        )


def upload_to_qdrant(chunks: Iterable[Mapping[str, Any]]) -> bool:
    """Embed document chunks and upload them to the configured Qdrant collection."""
    try:
        if not QDRANT_URL:
            raise ValueError("QDRANT_URL is missing. Check backend/.env")
        if not QDRANT_API_KEY:
            raise ValueError("QDRANT_API_KEY is missing. Check backend/.env")

        valid_chunks = [
            chunk for chunk in chunks
            if isinstance(chunk.get("content"), str) and chunk["content"].strip()
        ]
        if not valid_chunks:
            print("No non-empty chunks to upload")
            return False

        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=30, check_compatibility=False)
        print("Connected to Qdrant")

        # 🧠 เตรียมข้อมูล
        docs = [chunk["content"] for chunk in valid_chunks]
        metas = [dict(chunk.get("metadata", {})) for chunk in valid_chunks]

        vectors = get_embedding_model().embed_documents(docs)
        vector_size = len(vectors[0])

        # 📦 สร้าง collection ถ้ายังไม่มี / schema ว่าง / มิติไม่ตรงกับ embedding ปัจจุบัน
        collections = [c.name for c in client.get_collections().collections]
        if COLLECTION_NAME in collections:
            collection_info = client.get_collection(COLLECTION_NAME)
            existing_vectors = collection_info.config.params.vectors
            existing_size = None
            if isinstance(existing_vectors, models.VectorParams):
                existing_size = existing_vectors.size
            elif isinstance(existing_vectors, dict) and existing_vectors:
                # Named vectors config — take first size if present
                first = next(iter(existing_vectors.values()), None)
                if isinstance(first, models.VectorParams):
                    existing_size = first.size

            needs_recreate = (
                existing_vectors == {}
                or (existing_size is not None and existing_size != vector_size)
            )
            if needs_recreate:
                client.delete_collection(collection_name=COLLECTION_NAME)
                collections.remove(COLLECTION_NAME)
                print(
                    f"Recreated collection {COLLECTION_NAME} "
                    f"(old dim={existing_size}, new dim={vector_size})"
                )

        if COLLECTION_NAME not in collections:
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=models.VectorParams(
                    size=vector_size,
                    distance=models.Distance.COSINE
                )
            )
            print(f"Created collection: {COLLECTION_NAME} (dim={vector_size})")

        ensure_payload_indexes(client)

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
            print(f"Uploaded {i + 1} - {i + len(points)}")

        print("Upload complete")
        return True

    except Exception as e:
        print(f"Upload failed: {e}")
        return False


def _candidate_sources(filename: str | None, file_path: str | None) -> list[str]:
    """Build possible Qdrant `source` values used during scan/upload."""
    sources: set[str] = set()

    if file_path:
        base = os.path.basename(file_path)
        sources.add(base)
        # Final path is usually "{project_id}_{safe_filename}" while scan used "temp_{safe_filename}"
        if "_" in base:
            original = base.split("_", 1)[1]
            if original:
                sources.add(original)
                sources.add(f"temp_{original}")

    if filename:
        safe = filename.replace(" ", "_")
        sources.add(filename)
        sources.add(safe)
        sources.add(f"temp_{safe}")

    return sorted(s for s in sources if s)


def delete_from_qdrant(
    *,
    project_title: str | None = None,
    filename: str | None = None,
    file_path: str | None = None,
) -> bool:
    """
    Delete vector points for a document from Qdrant.

    Matches by project_title and/or source filename variants (including temp_* used at scan time).
    """
    try:
        if not QDRANT_URL:
            raise ValueError("QDRANT_URL is missing. Check backend/.env")
        if not QDRANT_API_KEY:
            raise ValueError("QDRANT_API_KEY is missing. Check backend/.env")

        conditions: list[models.FieldCondition] = []
        if project_title and project_title.strip():
            conditions.append(
                models.FieldCondition(
                    key="project_title",
                    match=models.MatchValue(value=project_title.strip()),
                )
            )

        sources = _candidate_sources(filename, file_path)
        if sources:
            conditions.append(
                models.FieldCondition(
                    key="source",
                    match=models.MatchAny(any=sources),
                )
            )

        if not conditions:
            print("delete_from_qdrant skipped: no project_title/source to match")
            return False

        client = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
            timeout=30,
            check_compatibility=False,
        )

        collections = [c.name for c in client.get_collections().collections]
        if COLLECTION_NAME not in collections:
            print(f"delete_from_qdrant skipped: collection {COLLECTION_NAME} not found")
            return True

        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=models.FilterSelector(
                filter=models.Filter(should=conditions)
            ),
        )
        print(
            "Deleted Qdrant vectors matching "
            f"title={project_title!r} sources={sources}"
        )
        return True
    except Exception as e:
        print(f"Qdrant vector delete failed: {e}")
        return False
