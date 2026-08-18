import os
from time import perf_counter

from rag.embedding.pdf_scanning import scan_pdf_document
from rag.embedding.text_processor import chunk_extracted_data
from rag.embedding.vector_store import upload_to_qdrant


def summarize(times):
    if not times:
        return

    total = sum(times)
    count = len(times)
    mean = total / count

    times_sorted = sorted(times)

    # median
    if count % 2 == 0:
        median = (times_sorted[count//2 - 1] + times_sorted[count//2]) / 2
    else:
        median = times_sorted[count//2]

    p90 = times_sorted[min(int(0.9 * count), count - 1)]
    p95 = times_sorted[min(int(0.95 * count), count - 1)]

    print("\n📊 ===== Performance Summary =====")
    print(f"📁 Files processed: {count}")
    print(f"📈 Total time: {total:.3f}s")
    print(f"📊 Mean: {mean:.3f}s")
    print(f"📍 Median: {median:.3f}s")
    print(f"📉 Min: {min(times):.3f}s")
    print(f"📈 Max: {max(times):.3f}s")
    print(f"🚀 P90: {p90:.3f}s")
    print(f"🔥 P95: {p95:.3f}s")
    print("=" * 40)


def process_file(file_path, preview=False,ENABLE_UPLOAD = True):
    start = perf_counter()
    file_name = os.path.basename(file_path)
    

    print(f"\n🚀 Processing: {file_name}")

    try:
        # 1. Scan
        pages = scan_pdf_document(file_path)
        if not pages:
            print("⚠️ No content found")
            return None

        print("✅ Scan complete")

        # 2. Chunk
        chunks = chunk_extracted_data(pages)
        print(f"🧩 Generated {len(chunks)} chunks")

        # Preview (เฉพาะไฟล์แรก)
        if preview:
            print("\n🔍 Preview (Chunks + Metadata):")

            for i, c in enumerate(chunks[:3]):
                print(f"\n🔹 Chunk {i+1}")

                # content
                print(f"📄 Content: {c['content'][:100]}...")

                # metadata
                print("🏷️ Metadata:")
                for key, value in c["metadata"].items():
                    print(f"   - {key}: {value}")

            print("-" * 30)

        # 3. Upload
        print("🧠 Uploading...")

        if ENABLE_UPLOAD:
            success = upload_to_qdrant(chunks)

            if success:
                print("✨ Upload success")
            else:
                print("❌ Upload failed")
        else:
            print("⏭️ Upload skipped (disabled)")

    except Exception as e:
        print(f"❌ Error: {e}")
        return None

    elapsed = perf_counter() - start
    print(f"⏱️ Time: {elapsed:.3f}s")

    return elapsed


def test_pipeline():
    target_dir = "./data/files_for_evaluation/"

    # ===== CONFIG =====
    MODE = "all"        # "all" | "specific" | "limit"
    TARGET_FILES = ["file1.pdf", "file2.pdf"]  # ใช้ตอน mode = specific
    LIMIT = 20         # ใช้ตอน mode = limit
    # ==================

    if not os.path.exists(target_dir):
        print(f"⚠️ Directory not found: {target_dir}")
        return

    files = [f for f in os.listdir(target_dir) if f.endswith(".pdf")]
    if not files:
        print("⚠️ No PDF files found")
        return

    # ===== SELECT FILES =====
    if MODE == "specific":
        files = [f for f in files if f in TARGET_FILES]

    elif MODE == "limit":
        files = files[:LIMIT]

    elif MODE == "all":
        pass  # ใช้ทั้งหมด

    else:
        print("❌ Invalid MODE")
        return
    # ========================

    print(f"🔍 Processing {len(files)} file(s)\n")

    times = []
    start_total = perf_counter()

    for i, file_name in enumerate(files):
        file_path = os.path.join(target_dir, file_name)

        elapsed = process_file(
            file_path,
            preview=(i == 0)
        )

        if elapsed:
            times.append(elapsed)

    total_time = perf_counter() - start_total

    print(f"\n⏱️ Total pipeline time: {total_time:.3f}s")
    summarize(times)

if __name__ == "__main__":
    test_pipeline()
