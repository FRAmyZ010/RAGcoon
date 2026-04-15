import os
import json
from time import perf_counter
from rag.embedding.pdf_scanning import scan_pdf_document

def test_pipeline():
    # define file path
    target_dir = "./data/final_doc/"
    target_file = "Book-Senior.pdf"  # ชื่อไฟล์ที่ต้องการแสกน

    # Checking directory
    if not os.path.exists(target_dir):
        print(f"⚠️ Error: Directory '{target_dir}' not found.")
        return
    
    # ตรวจสอบว่ามีไฟล์ที่ระบุอยู่จริงหรือไม่
    file_path = os.path.join(target_dir, target_file)
    if not os.path.exists(file_path):
        print(f"⚠️ Error: File '{target_file}' not found in {target_dir}")
        return
    
    print(f"🔍 Starting scanning for specific file: {target_file}\n")

    start = perf_counter()

    try:
        # เริ่มการสแกนเฉพาะไฟล์ที่ระบุ
        results = scan_pdf_document(file_path)
        print(f"✅ Success! Extracted {len(results)} pages.")

        # แสดงเนื้อหาเฉพาะ 5 หน้าแรก
        for page in results[:5]:
            p_num = page['metadata']['page_number']
            content = page['content']
            
            print(f"\n--- 📄 Page {p_num} ---")
            print(content)
            print(f"--- End of Page {p_num} ---")
        
        if len(results) > 5:
            print(f"\n... and {len(results) - 5} more pages were scanned but not displayed.")

        # โชว์ Metadata รวมของไฟล์นี้
        if results:
            print(f"\n📊 Metadata Detail: {json.dumps(results[0]['metadata'], indent=4, ensure_ascii=False)}")

        print("\n" + "="*50 + "\n")

    except Exception as e:
        print(f"❌ Failed to scan {target_file}: {str(e)}")
    
    end = perf_counter()
    print(f"⏱️ Total time taken: {end - start:.3f} seconds\n")

if __name__ == "__main__":
    test_pipeline()