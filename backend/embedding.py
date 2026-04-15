import os
import json
from time import perf_counter
from rag.embedding.pdf_scanning import scan_pdf_document

def test_pipeline():
    # define file path
    target_dir = "./data/final_doc/"

    # Checking directory and files
    if not os.path.exists(target_dir):
        print(f"⚠️ Error: Directory '{target_dir}' not found.")
        return
    
    pdf_files = [f for f in os.listdir(target_dir) if f.endswith('.pdf')]

    if not pdf_files:
        print(f"⚠️ No PDF files found in {target_dir}")
        return
    
    print(f"🔍 Found {len(pdf_files)} PDF(s). Starting scanning...\n")

    times = []
    round_num = 0

    for file_name in pdf_files:
        round_num += 1
        start = perf_counter()
        file_path = os.path.join(target_dir, file_name)
        
        print(f"🚀 Round {round_num}: Processing {file_name}")

        try:
            results = scan_pdf_document(file_path)
            print(f"✅ Success! Extracted {len(results)} pages.")

            # --- ส่วนที่เพิ่ม: Loop โชว์เนื้อหาทุกหน้า ---
            # --- ส่วนที่ปรับปรุง: Loop โชว์เนื้อหาเฉพาะ 5 หน้าแรก ---
            # ใช้ [:5] เพื่อดึงเฉพาะ 5 item แรกจาก list 'results'
            # for page in results[:5]:
            #     p_num = page['metadata']['page_number']
            #     content = page['content']
                
            #     print(f"\n--- 📄 Page {p_num} ---")
            #     print(content)
            #     print(f"--- End of Page {p_num} ---")
            
            # # แจ้งเตือนผู้ใช้หน่อยว่ายังมีหน้าอื่นที่ไม่ได้โชว์
            # if len(results) > 5:
            #     print(f"\n... and {len(results) - 5} more pages were scanned but not displayed.")
            # # ---------------------------------------------------

            # โชว์ Metadata รวมของไฟล์นี้ (ดูจากหน้าแรก)
            if results:
                print(f"\n📊 Global Metadata Sample: {json.dumps(results[0]['metadata'], indent=4, ensure_ascii=False)}")

            print("\n" + "="*50 + "\n")

        except Exception as e:
            print(f"❌ Failed to scan {file_name}: {str(e)}")
        
        end = perf_counter()
        elapsed = end - start
        times.append(elapsed)
        print(f"⏱️ Time taken for this file: {elapsed:.3f} seconds\n")

    # สรุปภาพรวม
    if times:
        print(f"📈 Total time: {sum(times):.3f} seconds")
        print(f"📊 Avg/File: {sum(times)/len(times):.3f} seconds")

if __name__ == "__main__":
    test_pipeline()