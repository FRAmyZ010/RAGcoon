from pathlib import Path
from typing import Any

from backend.app.rag.embedding.pdf_scanning import scan_pdf_document
from backend.app.rag.embedding.text_processor import chunk_extracted_data

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "files_for_evaluation"


def _print_metadata(pages: list[dict[str, Any]]) -> None:
	if not pages:
		print("No extracted pages found.")
		return

	metadata = pages[0]["metadata"]
	keys = (
		"source",
		"page_number",
		"total_pages",
		"project_title",
		"author",
		"advisor",
		"committee",
		"keywords",
		"year",
	)
	print("\n===== Metadata =====")
	for key in keys:
		print(f"{key}: {metadata.get(key)}")
	print(f"pages with extracted content: {len(pages)}")


def _print_chunks(chunks: list[dict[str, Any]]) -> None:
	if not chunks:
		print("No chunks found.")
		return

	print("\nChunk order:")
	print("1. Page ascending")
	print("2. Page descending")
	print("3. Content A-Z")
	order = input("Select order [1]: ").strip() or "1"

	if order == "2":
		chunks = sorted(
			chunks,
			key=lambda chunk: chunk["metadata"].get("page_number", 0),
			reverse=True,
		)
	elif order == "3":
		chunks = sorted(chunks, key=lambda chunk: chunk["content"].lower())
	elif order != "1":
		print("Invalid order. Using page ascending.")

	print(f"\n===== Content Chunks ({len(chunks)}) =====")
	for index, chunk in enumerate(chunks, start=1):
		page_number = chunk["metadata"].get("page_number", "?")
		print(f"\n----- Chunk {index}/{len(chunks)} | page {page_number} -----")
		print(chunk["content"])


def _select_file(pdf_files: list[Path]) -> Path | None:
	print("\n===== PDF Files =====")
	for index, path in enumerate(pdf_files, start=1):
		print(f"{index}. {path.name}")

	selection = input("Enter file number or exact filename (q to quit): ").strip()
	if selection.lower() == "q":
		return None

	if selection.isdigit():
		file_index = int(selection) - 1
		if 0 <= file_index < len(pdf_files):
			return pdf_files[file_index]
	else:
		for path in pdf_files:
			if path.name == selection:
				return path

	print("File not found. Please try again.")
	return Path("")


def debug_pdf() -> None:
	if not DATA_DIR.exists():
		print(f"PDF directory not found: {DATA_DIR}")
		return

	while True:
		pdf_files = sorted(DATA_DIR.glob("*.pdf"), key=lambda path: path.name.lower())
		if not pdf_files:
			print(f"No PDF files found in {DATA_DIR}")
			return

		selected_file = _select_file(pdf_files)
		if selected_file is None:
			print("Bye.")
			return
		if not selected_file.name:
			continue

		try:
			pages = scan_pdf_document(str(selected_file))
			chunks = chunk_extracted_data(pages)
		except Exception as error:
			print(f"Error reading {selected_file.name}: {error}")
			continue

		print(f"\nSelected: {selected_file.name}")
		while True:
			print("\n1. Show metadata")
			print("2. Show content chunks")
			print("3. Choose another PDF")
			print("q. Quit")
			choice = input("Select: ").strip().lower()

			if choice == "1":
				_print_metadata(pages)
			elif choice == "2":
				_print_chunks(chunks)
			elif choice == "3":
				break
			elif choice == "q":
				print("Bye.")
				return
			else:
				print("Invalid choice.")


if __name__ == "__main__":
	debug_pdf()
