from collections.abc import Iterable, Mapping
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_extracted_data(extracted_results: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """
    รับ list ของ dict ที่มี content และ metadata มาหั่นเป็น chunks
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
        separators=["\n\n", "\n", " ", ""]
    )

    all_chunks: list[dict[str, Any]] = []
    for page in extracted_results:
        content = page.get("content")
        metadata = page.get("metadata", {})

        if not isinstance(content, str) or not content.strip():
            continue
        if not isinstance(metadata, Mapping):
            raise ValueError("Each page's metadata must be a mapping.")

        chunks = text_splitter.split_text(content)
        for chunk in chunks:
            all_chunks.append({
                "content": chunk,
                "metadata": dict(metadata),
            })
    
    print(f"Total chunks created: {len(all_chunks)}")
    return all_chunks
