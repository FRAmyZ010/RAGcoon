import os
import glob
import pdfplumber
from dotenv import load_dotenv
from qdrant_client.http import models

from utils.scanner import scan_pdf
from utils.cleanser import clean_text
from utils.processor import create_chunks
from utils.metadata import extract_metadata
from utils.embedder import generate_embeddings
from utils.database import QdrantManager

load_dotenv()

DATA_FOLDER = "./data/dummy/"
COLLECTION_NAME = "project_documents"

def main():
    db_manager = QdrantManager(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY")
    )

    pdf_files = glob.glob(os.path.join(DATA_FOLDER, "*.pdf"))
    if not pdf_files:
        print(f"❌ No PDF files found in {DATA_FOLDER}")
        return

    all_points = []
    point_id_counter = 0

    for file_path in pdf_files:
        print(f"\n🚀 Processing: {os.path.basename(file_path)}")

        # 1. Scan
        with pdfplumber.open(file_path) as pdf:
            first_page_text = pdf.pages[0].extract_text() if pdf.pages else ""
            raw_text = ""
            for page in pdf.pages:
                content = page.extract_text()
                if content: raw_text += content + "\n"

        # 2. Clean
        cleaned_text = clean_text(raw_text)
        if not cleaned_text: continue

        # 3. Chunk
        chunks = create_chunks(cleaned_text)

        # 4. Metadata
        base_metadata = extract_metadata(file_path, first_page_text, 0)
        
        # 5. Embed
        embeddings = generate_embeddings(chunks)

        # 6. Prepare Points
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            payload = base_metadata.copy()
            payload["chunk_index"] = i
            payload["text"] = chunk
            
            all_points.append(
                models.PointStruct(
                    id=point_id_counter,
                    vector=emb.tolist(),
                    payload=payload
                )
            )
            point_id_counter += 1

    # Final Upload
    if all_points:
        print(f"\n📤 Uploading {len(all_points)} vectors to Qdrant Cloud...")
        db_manager.store_vectors(COLLECTION_NAME, all_points)
        print("✅ Finished!")

if __name__ == "__main__":
    main()