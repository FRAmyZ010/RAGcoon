import os
import json
from time import perf_counter
from rag.embedding.pdf_scanning import scan_pdf_document

times = []



def test_pipeline():
    # define file  path
    target_dir = "./data/final_doc/"

    # Checking directory and files
    if not os.path.exists(target_dir):
        print(f"⚠️ Error: Directory '{target_dir}' not found.")
        return
    
    pdf_files = [f for f in os.listdir(target_dir) if f.endswith('.pdf')]

    if not pdf_files:
        print(f"⚠️No PDF files found in {target_dir}")
        return
    
    print(f"🔍 Found {len(pdf_files)} PDF(s). Starting scanning...\n")

    round = 0
    # Start scanning each PDF
    for file_name in pdf_files:
        round += 1
        start = perf_counter()
        file_path = os.path.join(target_dir, file_name)
        print(f"📚 Scanning round {round}: {file_name}")

        try:
            results = scan_pdf_document(file_path)

            print(f"✅Success! Extract {len(results)} pages.")

            if results:
                first_page_content = results[0]['content']
                print(f"📄Preview (Page 1): {first_page_content}...")
                print(f"📊Metadata: {results[0]['metadata']}")

            print("-" * 30)
        except Exception as e:
            print(f"❌ Failed to scan {file_name}: {str(e)}")
        end = perf_counter()
        
        print(f"⏱️ Time taken: {end - start:.3f} seconds\n")

        elapsed = end - start
        times.append(elapsed)

    print(f"📈 Total time taken: {sum(times):.3f} seconds")
    print(f"📊 Average time per file: {sum(times)/len(times):.3f} seconds")

    print(f"📉 Min time: {min(times):.3f} seconds")
    print(f"📈 Max time: {max(times):.3f} seconds")

if __name__ == "__main__":
    test_pipeline()