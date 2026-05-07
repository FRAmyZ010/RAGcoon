import os #ใช้อ่านค่าจาก environment variables เช่น URL ของ Qdrant, API key, ชื่อ collection
import time #ใช้สำหรับวัดเวลาการประมวลผลของแต่ละ query เพื่อดูประสิทธิภาพ
from typing import List, Dict, Optional,Tuple #ใช้บอกชนิดข้อมูลให้ชัด เช่น List[str], Optional[Dict] ทำให้โค้ดอ่านง่ายและช่วยตอน lint / autocomplete
import re


from dotenv import load_dotenv # load_dotenv() ใช้โหลดค่าจากไฟล์ .env
from qdrant_client import QdrantClient # QdrantClient คือ client หลักสำหรับคุยกับฐานข้อมูลเวกเตอร์ Qdrant
from qdrant_client.http.exceptions import ResponseHandlingException # ResponseHandlingException ใช้จับ error เฉพาะกรณี request/response จาก Qdrant มีปัญหา เช่น timeout หรือ response ไม่ปกติ
from sentence_transformers import CrossEncoder # CrossEncoder ใช้สำหรับ reranking เอกสารโดยการให้คะแนนความเกี่ยวข้องระหว่าง query กับแต่ละ document
from langchain_huggingface import HuggingFaceEmbeddings # HuggingFaceEmbeddings ใช้สำหรับแปลง query เป็นเวกเตอร์ embedding เพื่อใช้ในการค้นหาแบบ semantic ใน Qdrant
from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchAny # Filter, FieldCondition, MatchValue, MatchAny ใช้สำหรับสร้างเงื่อนไขการกรอง (filter) ในการค้นหาเอกสารใน Qdrant เช่น กรองตาม metadata หรือ field อื่นๆ

from performance import format_performance_summary # format_performance_summary ใช้สำหรับสรุปผลการวัดประสิทธิภาพของการค้นหา เช่น เวลาที่ใช้ในการประมวลผลแต่ละ query และสถิติต่างๆ เช่น mean, median, p90, p95

# =========================
# ENV & INIT
# =========================
load_dotenv() # โหลดค่าจากไฟล์ .env เพื่อให้สามารถใช้ environment variables ได้ เช่น QDRANT_URL, QDRANT_API_KEY, EMBEDDING_MODEL, COLLECTION_NAME, RETRIEVAL_TOP_K, RETRIEVAL_TOP_N

QDRANT_URL = os.getenv("QDRANT_URL") # QDRANT_URL คือ URL ของ Qdrant server ที่เราจะเชื่อมต่อ เช่น http://localhost:11434 หรือ URL ของบริการ Qdrant ที่โฮสต์อยู่บนคลาวด์
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY") # QDRANT_API_KEY คือ API key สำหรับการยืนยันตัวตนเมื่อเชื่อมต่อกับ Qdrant server ถ้า Qdrant server ของเราตั้งค่าให้ต้องใช้ API key ในการเข้าถึง เราจะต้องใส่ค่า API key นี้เพื่อให้สามารถทำการค้นหาและจัดการข้อมูลใน Qdrant ได้

if not QDRANT_URL: # ถ้า QDRANT_URL ไม่ถูกตั้งค่าใน environment variables จะเกิด error และไม่สามารถเชื่อมต่อกับ Qdrant ได้ ดังนั้นเราจะเช็คและแจ้ง error ทันทีเพื่อให้ผู้ใช้รู้ว่าต้องตั้งค่า QDRANT_URL ก่อนที่จะใช้งาน
    raise ValueError("QDRANT_URL is not set")

if not QDRANT_API_KEY: # ถ้า QDRANT_API_KEY ไม่ถูกตั้งค่าใน environment variables จะเกิด error และไม่สามารถเชื่อมต่อกับ Qdrant ได้ ดังนั้นเราจะเช็คและแจ้ง error ทันทีเพื่อให้ผู้ใช้รู้ว่าต้องตั้งค่า QDRANT_API_KEY ก่อนที่จะใช้งาน
    raise ValueError("QDRANT_API_KEY is not set")

client = QdrantClient( # อันนี้คือการสร้าง connection ไป Qdrant 
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
    timeout=int(os.getenv("QDRANT_TIMEOUT", "30")), # timeout กัน request ค้างนานเกินไป
    check_compatibility=False, # check_compatibility=False มักใส่เมื่อไม่อยากให้ client ไปเช็กเวอร์ชันลึก ๆ ตอนเริ่มต้น
)

# =========================
# CONFIG    EMBEDDING_MODEL คือโมเดลที่ใช้แปลง query เป็น vector
#           COLLECTION_NAME คือชื่อ collection ใน Qdrant
#           DEFAULT_TOP_K คือจำนวนผลที่ดึงจาก retrieval รอบแรก
#           DEFAULT_TOP_N คือจำนวนผลสุดท้ายหลัง rerank

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-base")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "embedding_evaluation")

DEFAULT_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "20"))
DEFAULT_TOP_N = int(os.getenv("RERANK_TOP_N", "5"))

# embed_model ใช้สร้าง vector สำหรับ semantic search
# reranker ใช้คำนวณความสัมพันธ์ query กับ doc แบบละเอียดในขั้นสุดท้าย

embed_model = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

# =========================
# QUERY UTILS
# =========================
def normalize_query(query: str) -> str:
    normalized = " ".join(query.strip().split())

    replacements = {
        "methology": "methodology",
        "methodolgy": "methodology",
        "petfeeder": "pet feeder",
    }

    lowered = normalized.lower() # ทำให้ query เป็นตัวพิมพ์เล็กทั้งหมดเพื่อช่วยในการแมตช์คำที่อาจสะกดผิดหรือมีรูปแบบต่าง ๆ กัน เช่น "methology" กับ "methodology" หรือ "petfeeder" กับ "pet feeder" ซึ่งจะช่วยเพิ่มโอกาสในการค้นหาเอกสารที่เกี่ยวข้องได้มากขึ้น
    for src, tgt in replacements.items(): # ทำการลูปผ่านคำที่ต้องการแทนที่ใน query และแทนที่ด้วยคำที่ถูกต้องตามที่กำหนดไว้ใน dictionary replacements ซึ่งจะช่วยให้ query มีความแม่นยำมากขึ้นและเพิ่มโอกาสในการค้นหาเอกสารที่เกี่ยวข้องได้มากขึ้น
        lowered = lowered.replace(src, tgt) # ทำการแทนที่คำที่สะกดผิดหรือมีรูปแบบต่าง ๆ กันใน query ด้วยคำที่ถูกต้องตามที่กำหนดไว้ใน dictionary replacements ซึ่งจะช่วยให้ query มีความแม่นยำมากขึ้นและเพิ่มโอกาสในการค้นหาเอกสารที่เกี่ยวข้องได้มากขึ้น
    return lowered # หลังจากนั้นคือค่าที่ถูก normalize แล้วจะถูกส่งกลับมาใช้ในการค้นหาเอกสารใน Qdrant ซึ่งจะช่วยเพิ่มโอกาสในการค้นหาเอกสารที่เกี่ยวข้องได้มากขึ้นและลดปัญหาจากการสะกดผิดหรือรูปแบบต่าง ๆ ของคำใน query


# =========================
# FILTER
# =========================

def extract_query_and_filters(user_query: str) -> Tuple[str, Dict]: # 
    filters = {} # หลังจากที่รับค่า จาก normalize  ฟังชันก์นี้ จะทำการแยกข้อความ เพื่อ จะทำการ สร้าง filters เอาไว้เก็บเงื่อนไข metadata (key-value)  
    
    # หา year
    year_match = re.search(r"\b(19\d{2}|20\d{2})\b", user_query) # โดยอย่างแรกคือการแยก ปี ออกจากคำถาม หา "ปี" ด้วย regex
    if year_match:
        filters["year"] = year_match.group() # regex นี้จะค้นหาเลขที่เป็นปีในรูปแบบ 4 หลักที่ขึ้นต้นด้วย 19 หรือ 20 และถ้าพบจะนำค่าที่จับได้มาเก็บใน filters dictionary โดยใช้ key เป็น "year" และ value เป็นปีที่จับได้ ซึ่งจะช่วยให้ได้ผลลัพธ์ที่ตรงกับความต้องการมากขึ้นและลดจำนวนเอกสารที่ไม่เกี่ยวข้องที่ถูกดึงมาในการค้นหา

    # clean query
    clean_query = re.sub(r"\b(19\d{2}|20\d{2})\b", "", user_query)  # ทำความสะอาด query โดยการลบปีออกจาก query เพื่อให้ clean_query เป็นส่วนที่เหลือของ query ที่ถูกทำความสะอาดแล้ว ซึ่งจะช่วยเพิ่มโอกาสในการค้นหาเอกสารที่เกี่ยวข้องได้มากขึ้นและลดปัญหาจากการสะกดผิดหรือรูปแบบต่าง ๆ ของคำใน query
    clean_query = clean_query.strip() # ทำความสะอาด query โดยการลบช่องว่างที่เกินออกจาก clean_query เพื่อให้ clean_query เป็นส่วนที่เหลือของ query ที่ถูกทำความสะอาดแล้ว ซึ่งจะช่วยเพิ่มโอกาสในการค้นหาเอกสารที่เกี่ยวข้องได้มากขึ้นและลดปัญหาจากการสะกดผิดหรือรูปแบบต่าง ๆ ของคำใน query

    return clean_query, filters  # หลังจากที่ได้แยก query และส่วนที่เป็น filters ออกมาแล้ว ฟังก์ชันนี้จะส่งกลับ clean_query ซึ่งเป็นส่วนที่เหลือของ query ที่ถูกทำความสะอาดแล้ว และ filters ซึ่งเป็น dictionary ที่เก็บเงื่อนไขการกรองข้อมูลที่ถูกแยกออกมาจาก query เช่น ถ้า query มีคำว่า "ปี 2020" ฟังก์ชันนี้จะสามารถแยก "ปี 2020" ออกมาเป็น filter ที่บอกว่าให้ค้นหาเฉพาะเอกสารที่มี field "year" เท่ากับ 2020 และ clean_query จะเป็นส่วนที่เหลือของ query ที่ถูกทำความสะอาดแล้ว ซึ่งจะช่วยเพิ่มโอกาสในการค้นหาเอกสารที่เกี่ยวข้องได้มากขึ้นและลดปัญหาจากการสะกดผิดหรือรูปแบบต่าง ๆ ของคำใน query


def build_qdrant_filter(filters: Optional[Dict]) -> Optional[Filter]: # ฟังก์ชันนี้ใช้สร้าง format filter สำหรับการค้นหาใน Qdrant โดยรับพารามิเตอร์เป็น dictionary ที่มี key เป็นชื่อ field และ value เป็นค่าที่ต้องการกรอง ซึ่งสามารถเป็นค่าเดียวหรือ list ของค่าที่ต้องการกรองได้ เช่น {"type": "pdf", "created_at": ["2023-01-01", "2023-12-31"]} ซึ่งจะกรองเอกสารที่มี type เป็น pdf และ created_at อยู่ในช่วงวันที่กำหนด
    if not filters: # เช็คว่ามี filter ไหม ถ้าไม่มี None → Qdrant จะ “ค้นทั้ง collection”
        return None

    conditions = [] # สร้าง list ว่างไว้เก็บ “เงื่อนไขการกรองข้อมูล”
                    # เช่น ถ้า query ระบุเฉพาะ document ที่ year = 2023 เท่านั้น ระบบจะสร้างเงื่อนไขการกรองข้อมูลที่บอกว่าให้ค้นหาเฉพาะ document ที่มี field "year" เท่ากับ 2023 เท่านั้น ซึ่งจะช่วยให้ได้ผลลัพธ์ที่ตรงกับความต้องการมากขึ้นและลดจำนวนเอกสารที่ไม่เกี่ยวข้องที่ถูกดึงมาในการค้นหา
                
    for key, value in filters.items(): # ลูปผ่านแต่ละ key-value pair ใน filters dictionary (metadata )เพื่อสร้างเงื่อนไขการกรองข้อมูลสำหรับแต่ละ field ที่ต้องการกรอง เช่น ถ้า filters มี {"type": "pdf", "created_at": ["2023-01-01", "2023-12-31"]} 
                                       # จะมีการลูปผ่านสองรอบคือรอบแรก key = "type" และ value = "pdf" ซึ่งจะสร้างเงื่อนไขการกรองข้อมูลที่บอกว่าให้ค้นหาเฉพาะ document ที่มี field "type" เท่ากับ "pdf" 
                                       # และรอบที่สอง key = "created_at" และ value = ["2023-01-01", "2023-12-31"] ซึ่งจะสร้างเงื่อนไขการกรองข้อมูลที่บอกว่าให้ค้นหาเฉพาะ document ที่มี field "created_at" อยู่ในช่วงวันที่กำหนด
        if isinstance(value, list):
            conditions.append(
                FieldCondition(key=key, match=MatchAny(any=value))
            )
        else:
            conditions.append(
                FieldCondition(key=key, match=MatchValue(value=value))
            )

    return Filter(must=conditions) # หลังจากสร้างเงื่อนไขการกรองข้อมูลสำหรับแต่ละ field ที่ต้องการกรองแล้ว เงื่อนไขเหล่านั้นจะถูกนำมารวมกันในรูปแบบของ Filter ที่มีเงื่อนไขทั้งหมดอยู่ใน must ซึ่งหมายความว่าเอกสารที่ถูกค้นหาจะต้องตรงกับทุกเงื่อนไขที่กำหนดไว้ใน must เท่านั้นถึงจะถูกดึงมาในการค้นหาใน Qdrant ซึ่งจะช่วยให้ได้ผลลัพธ์ที่ตรงกับความต้องการมากขึ้นและลดจำนวนเอกสารที่ไม่เกี่ยวข้องที่ถูกดึงมาในการค้นหา


# =========================
# SEARCH CORE (SEMANTIC ONLY)
# =========================
def semantic_search(query: str, top_k: int, metadata_filters=None) -> List[Dict]:
    query_vector = embed_model.embed_query(f"query: {query}") #
    query_filter = build_qdrant_filter(metadata_filters)

    try:
        results = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=top_k,
            with_payload=True,
            query_filter=query_filter,
        )
    except ResponseHandlingException:
        return []
    except Exception as e:
        return []

    return [
        {"text": p.payload["content"], "score": p.score}
        for p in results.points
        if p.payload and p.payload.get("content")
    ]

# =========================
# RERANK
# =========================
def normalize_scores(scores: List[float]) -> List[float]:
    if not scores:
        return []

    min_s = min(scores)
    max_s = max(scores)

    # กันหาร 0 (กรณี score เท่ากันหมด)
    if max_s - min_s == 0:
        return [1.0 for _ in scores]

    return [(s - min_s) / (max_s - min_s) for s in scores]

def rerank(query: str, docs: List[str], top_n: int) -> List[Dict]: # โดย รับ : query และ เอกสารที่ semantic หาได้ top_n นำมาให้ คะแนน ใหม่
    if not docs: # กัน error ถ้าไม่มีข้อมูล จะส่ง [] กลับไปเลย
        return []

    pairs = [[query, doc] for doc in docs] # สร้างคู่ของ query กับแต่ละ document ในรูปแบบของ list ที่มีสอง element คือ query และ doc ซึ่งจะถูกใช้เป็น input ให้กับ reranker ในการคำนวณความเกี่ยวข้องระหว่าง query กับแต่ละ document เพื่อให้ได้คะแนนความเกี่ยวข้องที่แม่นยำมากขึ้นในการจัดอันดับเอกสารที่เกี่ยวข้องกับ query มากที่สุด
    scores = reranker.predict(pairs) # ใช้ reranker ที่เป็น CrossEncoder ในการคำนวณความเกี่ยวข้องระหว่าง query กับแต่ละ document โดยการส่ง pairs ที่ประกอบด้วย query และ doc เป็น input ให้กับ reranker ซึ่งจะทำการประมวลผลและให้คะแนนความเกี่ยวข้องออกมาเป็น list ของ scores ที่มีค่าเป็นตัวเลขที่แสดงถึงความเกี่ยวข้องระหว่าง query กับแต่ละ document ซึ่งจะถูกใช้ในการจัดอันดับเอกสารที่เกี่ยวข้องกับ query มากที่สุดในขั้นตอนถัดไป

    ranked = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)  # (doc, score) โดยการใช้ฟังก์ชัน sorted() เพื่อจัดอันดับเอกสารที่เกี่ยวข้องกับ query มากที่สุดโดยการเรียงลำดับคู่ของ document และ score ที่ได้จาก reranker โดยใช้คะแนนความเกี่ยวข้อง (score) เป็นเกณฑ์ในการจัดอันดับและเรียงลำดับในรูปแบบจากมากไปน้อย (reverse=True) ซึ่งจะทำให้เอกสารที่มีความเกี่ยวข้องสูงสุดกับ query อยู่ในตำแหน่งแรกของ ranked list และเอกสารที่มีความเกี่ยวข้องต่ำสุดอยู่ในตำแหน่งสุดท้ายของ ranked list
    top_docs = ranked[:top_n] # เอาแค่ top N (เช่น 5 ตัว)

    norm_scores = normalize_scores([s for _, s in top_docs]) # ทำ normalization คะแนน (เช่น 0–1) เปรียบเทียบง่าย และช่วยให้การนำไปใช้ในขั้นตอนถัดไปมีความสอดคล้องกันมากขึ้น เช่น การนำคะแนนไปคำนวณร่วมกับคะแนนจากการค้นหาแบบอื่น ๆ หรือการแสดงผลคะแนนในรูปแบบที่เข้าใจง่ายขึ้นสำหรับผู้ใช้ ซึ่งจะช่วยให้ได้ผลลัพธ์ที่แม่นยำและมีความเกี่ยวข้องมากขึ้นกับ query ที่ต้องการค้นหา

    return [ # สุดท้ายส่งกลับเป็น list ของ dict ที่มี text และ score โดยที่ text คือเนื้อหาของ document และ score คือคะแนนความเกี่ยวข้องที่ได้จาก reranker หลังจากทำ normalization แล้ว ซึ่งจะช่วยให้ได้ผลลัพธ์ที่แม่นยำและมีความเกี่ยวข้องมากขึ้นกับ query ที่ต้องการค้นหา
        {"text": doc, "score": float(norm)}
        for (doc, _), norm in zip(top_docs, norm_scores)
    ]


# =========================
# MAIN SEARCH (CLEAN)
# =========================
def search(query: str) -> List[str]:
    print("\n" + "=" * 60)
    print("🧠 ORIGINAL QUERY:", query)

    query = normalize_query(query) # ทำการ normalize query 
    print("🔧 NORMALIZED QUERY:", query) # แล้วทำการโชว์

    # 👉 เพิ่มตรงนี้ (สำคัญ)
    clean_query, filters = extract_query_and_filters(query) # ฟังก์ชัน extract_query_and_filters() ใช้สำหรับแยก query ที่ถูก normalize และส่วนที่เป็น filters ซึ่งจะช่วยให้เราสามารถใช้ clean_query ในการค้นหาเอกสารใน Qdrant ได้อย่างมีประสิทธิภาพมากขึ้น และใช้ filters ในการกรองเอกสารที่ไม่เกี่ยวข้องออกไปได้มากขึ้น เช่น ถ้า query มีคำว่า "ปี 2020" ฟังก์ชันนี้จะสามารถแยก "ปี 2020" ออกมาเป็น filter ที่บอกว่าให้ค้นหาเฉพาะเอกสารที่มี field "year" เท่ากับ 2020 และ clean_query จะเป็นส่วนที่เหลือของ query ที่ถูกทำความสะอาดแล้ว ซึ่งจะช่วยเพิ่มโอกาสในการค้นหาเอกสารที่เกี่ยวข้องได้มากขึ้นและลดปัญหาจากการสะกดผิดหรือรูปแบบต่าง ๆ ของคำใน query

    print("🧹 CLEAN QUERY:", clean_query)
    print("📦 FILTERS:", filters)

    qdrant_filter = build_qdrant_filter(filters)
    print("🧱 QDRANT FILTER:", qdrant_filter)

    # 🔍 semantic search + filter
    results = semantic_search(clean_query, DEFAULT_TOP_K, metadata_filters=filters) 

    if not results:
        print("❌ No results after semantic + filter")
        return []

    print(f"📊 Retrieved (before rerank): {len(results)} docs")

    # 🧾 เอา text
    docs = [r["text"] for r in results]

    # 🧠 rerank
    reranked = rerank(clean_query, docs, DEFAULT_TOP_N)

    print(f"🏆 Top after rerank: {len(reranked)} docs")

    return [r["text"] for r in reranked]


def search_with_details(query: str) -> dict:
    """Search and return detailed results with scores and any errors."""
    total_start = time.perf_counter()
    try:
            
        print("\n" + "=" * 60)

        normalized_query = normalize_query(query)

        clean_query, filters = extract_query_and_filters(normalized_query)
        qdrant_filter = build_qdrant_filter(filters)

        # 🔍 semantic search + filter
        retrieval_start = time.perf_counter()
        results = semantic_search(clean_query, DEFAULT_TOP_K, metadata_filters=filters)
        retrieval_seconds = time.perf_counter() - retrieval_start

        if not results:
            print("❌ No results after semantic + filter")
            total_seconds = time.perf_counter() - total_start
            return {
                "results": [],
                "errors": [],
                "timing": {
                    "retrieval_seconds": retrieval_seconds,
                    "rerank_seconds": 0.0,
                    "total_seconds": total_seconds,
                },
                "normalized_query": normalized_query,
                "query_variants": [],
                "retrieved_count": 0,
            }

        docs = [r["text"] for r in results]

        # 🧠 rerank
        rerank_start = time.perf_counter()
        reranked = rerank(clean_query, docs, DEFAULT_TOP_N)
        rerank_seconds = time.perf_counter() - rerank_start

        total_seconds = time.perf_counter() - total_start
        
        return {
            "results": reranked,
            "errors": [],
            "timing": {
                "retrieval_seconds": retrieval_seconds,
                "rerank_seconds": rerank_seconds,
                "total_seconds": total_seconds,
            },
            "normalized_query": normalized_query,
            "query_variants": [],
            "retrieved_count": len(results),
        }
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error in search_with_details: {error_msg}")
        total_seconds = time.perf_counter() - total_start
        return {
            "results": [],
            "errors": [error_msg],
            "timing": {
                "retrieval_seconds": 0.0,
                "rerank_seconds": 0.0,
                "total_seconds": total_seconds,
            },
            "normalized_query": query,
            "query_variants": [],
            "retrieved_count": 0,
        }

# =========================
# DEBUG / TEST
# =========================

def run_sample_queries(queries: List[str]) -> None:

    print("\n" + "=" * 50)
    print("📚 Senior Project Document QA System")
    print("=" * 50)

    for idx, q in enumerate(queries, 1):

        start = time.perf_counter()

        # search
        results = search(q)

        elapsed = time.perf_counter() - start


        print("📌 RESULT")
        print("=" * 50)

        print(f"🔎 Query: {q}\n")

        if not results:
            print("❌ No results found")

        else:
            print("✅ Documents retrieved successfully")

        print("\n" + "-" * 50)
        print(f"⏱️ Time: {elapsed:.3f} seconds")
        print("=" * 50)


if __name__ == "__main__":
    SAMPLE_QUERIES = [
        "Requesting a project for the year 2020.",
    ]

    run_sample_queries(SAMPLE_QUERIES)