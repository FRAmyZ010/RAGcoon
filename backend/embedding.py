import os
import json
from time import perf_counter
from rag.embedding.pdf_scanning import scan_pdf_document

def test_pipeline():
    # define file path
    target_dir = "./data/final_doc/"

    # Checking directory
    if not os.path.exists(target_dir):
        print(f"⚠️ Error: Directory '{target_dir}' not found.")
        return
    
    # ดึงรายชื่อไฟล์ PDF ทั้งหมด
    all_files = [f for f in os.listdir(target_dir) if f.endswith('.pdf')]
    
    if not all_files:
        print(f"⚠️ No PDF files found in {target_dir}")
        return

    # เลือกสแกนเพียง 10 ไฟล์แรก
    target_files = all_files[40:50]
    
    print(f"🔍 Found {len(all_files)} files. Starting scanning for the first {len(target_files)} files...\n")

    times = []
    start_total = perf_counter()

    for index, file_name in enumerate(target_files):
        round_num = index + 1
        file_path = os.path.join(target_dir, file_name)
        start_file = perf_counter()
        
        print(f"🚀 Round {round_num}: Processing {file_name}")

        try:
            results = scan_pdf_document(file_path)
            print(f"✅ Success! Extracted {len(results)} pages.")

            # --- เงื่อนไข: โชว์เนื้อหา 5 หน้าแรก เฉพาะไฟล์แรกที่สแกนเพื่อตรวจสอบ ---
            if round_num == 1:
                print(f"\n--- 📝 Previewing content for the first file ({file_name}) ---")
                for page in results[:5]:
                    p_num = page['metadata']['page_number']
                    print(f"\n[Page {p_num}]")
                    print(page['content'][:500] + "...") # โชว์แค่ 500 ตัวอักษรแรกของแต่ละหน้าเพื่อความสะอาด
                print("\n" + "-"*30)

            # โชว์ Metadata สรุปของทุกไฟล์
            if results:
                print(f"📊 Metadata: {json.dumps(results[0]['metadata'], indent=4, ensure_ascii=False)}")

        except Exception as e:
            print(f"❌ Failed to scan {file_name}: {str(e)}")
        
        end_file = perf_counter()
        elapsed = end_file - start_file
        times.append(elapsed)
        print(f"⏱️ Time: {elapsed:.3f}s\n" + "-"*50)

    end_total = perf_counter()
    
    # สรุปผลลัพธ์
    print("\n" + "="*50)
    print(f"📈 Total time for {len(times)} files: {end_total - start_total:.3f} seconds")
    if times:
        print(f"📊 Average time per file: {sum(times)/len(times):.3f} seconds")
    print("="*50)

if __name__ == "__main__":
    test_pipeline()