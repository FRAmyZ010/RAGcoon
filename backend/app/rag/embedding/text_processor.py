from langchain_text_splitters import RecursiveCharacterTextSplitter

def chunk_extracted_data(extracted_results):
    """
    รับ list ของ dict ที่มี content และ metadata มาหั่นเป็น chunks
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
        separators=["\n\n", "\n", " ", ""]
    )

    all_chunks = []
    for page in extracted_results:
        chunks = text_splitter.split_text(page['content'])
        for chunk in chunks:
            all_chunks.append({
                "content": chunk,
                "metadata": page['metadata']
            })
    
    print(f"✂️  Total chunks created: {len(all_chunks)}")
    return all_chunks