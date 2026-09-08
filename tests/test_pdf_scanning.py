from backend.app.rag.embedding import pdf_scanning


class FakePage:
    def __init__(self, text: str):
        self._text = text

    def extract_text(self, x_tolerance=1, y_tolerance=2):
        return self._text


class FakePdf:
    def __init__(self, pages):
        self.pages = pages

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


def test_scan_pdf_document_keeps_page_numbers_aligned_with_scan(monkeypatch, tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    fake_pages = [
        FakePage("Page one content"),
        FakePage(""),
        FakePage("Page three content"),
    ]

    monkeypatch.setattr(pdf_scanning.pdfplumber, "open", lambda path: FakePdf(fake_pages))
    monkeypatch.setattr(pdf_scanning, "extract_project_metadata", lambda text: {})

    pages = pdf_scanning.scan_pdf_document(str(pdf_path))

    assert [page["metadata"]["page_number"] for page in pages] == [1, 2, 3]
    assert [page["content"] for page in pages] == ["Page one content", "", "Page three content"]
