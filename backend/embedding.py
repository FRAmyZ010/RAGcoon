import os
import json
from time import perf_counter

from rag.embedding.pdf_scanning import scan_pdf_document
from rag.embedding.text_processor import chunk_extracted_data
from rag.embedding.vector_store import upload_to_qdrant

def test_pipeline():
    target_dir = "./data/final_doc/"

    if not os.path.exists(target_dir):
        print(f"⚠️ Error: Directory '{target_dir}' not found.")
        return
    
    all_files = [f for f in os.listdir(target_dir) if f.endswith('.pdf')]
    if not all_files:
        print(f"⚠️ No PDF files found in {target_dir}")
        return

    target_files = ["Proposal Document.docx.pdf"]
    print(f"🔍 Found {len(all_files)} files. Starting RAG Pipeline...\n")

    times = []
    start_total = perf_counter()

    for index, file_name in enumerate(target_files):
        round_num = index + 1
        file_path = os.path.join(target_dir, file_name)
        start_file = perf_counter()
        
        print(f"🚀 Round {round_num}: Processing {file_name}")

        try:
            # --- STEP 1: Scanning ---
            results = scan_pdf_document(file_path)
            if not results:
                continue
            
            print(f"✅ Scanning Success!")

            # --- STEP 2: Chunking ---
            chunks = chunk_extracted_data(results)
            
            if round_num == 1:
                print(f"\n--- 🧩 Previewing Chunks for: {file_name} ---")
                
                for i, chunk in enumerate(chunks[:20]):
                    print(f"\n🔹 Chunk {i+1}/{len(chunks)}")
                    print(f"📄 Content: {chunk['content']}...") # โชว์แค่ 200 ตัวแรก
                    print("🏷️ Metadata:")
                    for key, value in chunk['metadata'].items():
                        print(f"   - {key}: {value}")
                print("\n" + "—"*30)

            # --- STEP 3: Embedding & Upload ---
            # ผมใส่ input() ไว้ให้คุณกดยืนยันก่อนยิงขึ้น Qdrant (เฉพาะไฟล์แรก)
            if round_num == 1:
                confirm = input("❓ Chunks look okay? Press Enter to upload to Qdrant (or type 's' to skip): ")
                if confirm.lower() == 's':
                    print("⏭️ Skipped upload for this file.")
                    continue

            print(f"🧠 Uploading {len(chunks)} chunks to Qdrant...")
            success = upload_to_qdrant(chunks)
            
            if success:
                print(f"✨ Successfully ingested {file_name}")
            else:
                print(f"❌ Failed to upload {file_name}")

        except Exception as e:
            print(f"❌ Pipeline Error on {file_name}: {str(e)}")
        
        end_file = perf_counter()
        elapsed = end_file - start_file
        times.append(elapsed)
        print(f"⏱️ Time: {elapsed:.3f}s\n" + "-"*50)

    end_total = perf_counter()
    print(f"\n📈 Finished! Total time: {end_total - start_total:.3f}s")

if __name__ == "__main__":
    test_pipeline()
# import os
# import json
# from time import perf_counter
# from rag.embedding.pdf_scanning import scan_pdf_document

# def test_pipeline():
#     # define file path
#     target_dir = "./data/final_doc/"

#     # Checking directory
#     if not os.path.exists(target_dir):
#         print(f"⚠️ Error: Directory '{target_dir}' not found.")
#         return
    
#     # ดึงรายชื่อไฟล์ PDF ทั้งหมด
#     all_files = [f for f in os.listdir(target_dir) if f.endswith('.pdf')]
    
#     if not all_files:
#         print(f"⚠️ No PDF files found in {target_dir}")
#         return

    
#     # target_files = ["Final Document(8).pdf"]
#     target_files = all_files
    
#     print(f"🔍 Found {len(all_files)} files. Starting scanning for the first {len(target_files)} files...\n")

#     times = []
#     start_total = perf_counter()

#     for index, file_name in enumerate(target_files):
#         round_num = index + 1
#         file_path = os.path.join(target_dir, file_name)
#         start_file = perf_counter()
        
#         print(f"🚀 Round {round_num}: Processing {file_name}")

#         try:
#             results = scan_pdf_document(file_path)
#             print(f"✅ Success! Extracted {len(results)} pages.")

#             # --- เงื่อนไข: โชว์เนื้อหา 5 หน้าแรก เฉพาะไฟล์แรกที่สแกนเพื่อตรวจสอบ ---
#             if round_num == 1:
#                 print(f"\n--- 📝 Previewing content for the first file ({file_name}) ---")
#                 for page in results[:5]:
#                     p_num = page['metadata']['page_number']
#                     print(f"\n[Page {p_num}]")
#                     print(page['content'][:500] + "...") # โชว์แค่ 500 ตัวอักษรแรกของแต่ละหน้าเพื่อความสะอาด
#                 print("\n" + "-"*30)

#             # โชว์ Metadata สรุปของทุกไฟล์
#             if results:
#                 print(f"📊 Metadata: {json.dumps(results[0]['metadata'], indent=4, ensure_ascii=False)}")

#         except Exception as e:
#             print(f"❌ Failed to scan {file_name}: {str(e)}")
        
#         end_file = perf_counter()
#         elapsed = end_file - start_file
#         times.append(elapsed)
#         print(f"⏱️ Time: {elapsed:.3f}s\n" + "-"*50)

#     end_total = perf_counter()
    
#     # สรุปผลลัพธ์
#     print("\n" + "="*50)
#     print(f"📈 Total time for {len(times)} files: {end_total - start_total:.3f} seconds")
#     if times:
#         print(f"📊 Average time per file: {sum(times)/len(times):.3f} seconds")
#     print("="*50)

# if __name__ == "__main__":
#     test_pipeline()