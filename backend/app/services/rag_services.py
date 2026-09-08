import sys
from pathlib import Path

# กำหนด Path ให้ชี้ไปยังโฟลเดอร์ app/rag เพื่อ Import retrieval ได้โดยตรง
RAG_DIR = Path(__file__).resolve().parent.parent / "rag"
if str(RAG_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_DIR))

from rag.retrieval import answer_question  # Import ฟังก์ชันของด๋อย[cite: 2]

class RAGService:
    async def get_answer(self, user_query: str) -> dict:
        """
        เรียกใช้ RAG Pipeline จริง แล้วแปลง Data Structure ส่งกลับให้ API Controller
        """
        # เรียกใช้ฟังก์ชันหลักของ RAG Engine[cite: 2]
        rag_result = answer_question(user_query)
        
        # ดึงข้อมูลจาก Dictionary ที่ RAG คืนค่ากลับมา[cite: 2]
        answer_text = rag_result.get("answer", "")
        sources = rag_result.get("sources", [])
        
        # แปลง sources (list of str) เป็น List ของ Citations Dict ตาม Schema ที่วางไว้[cite: 1, 2]
        citations = [{"source": src} for src in sources]
        
        return {
            "answer": answer_text,
            "citations": citations,
            "raw_result": rag_result  # (Optional) เก็บไว้ลง DB ในช่อง retrieved_docs หรือ logs[cite: 1]
        }

rag_service = RAGService()