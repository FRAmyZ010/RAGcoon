from sentence_transformers import SentenceTransformer

model = SentenceTransformer('intfloat/multilingual-e5-base')

def generate_embeddings(chunks):
    # สำหรับ E5 ต้องใส่ prefix 'passage: '
    chunks_with_prefix = [f"passage: {c}" for c in chunks]
    return model.encode(chunks_with_prefix)