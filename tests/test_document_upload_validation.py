"""Lightweight upload validation checks for Sprint 2 QA (stdlib unittest)."""
import os
import tempfile
import unittest

from app.services.document_service import (
    MAX_TOTAL_UPLOAD_BYTES,
    DocumentUploadError,
    DuplicateDocumentError,
    _assert_pdf_file,
)


class UploadValidationTests(unittest.TestCase):
    def test_reject_empty_file(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            path = tmp.name
        try:
            with self.assertRaises(DocumentUploadError) as ctx:
                _assert_pdf_file(path, "empty.pdf")
            self.assertIn("ว่าง", ctx.exception.message)
        finally:
            os.remove(path)

    def test_reject_non_pdf_header(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"NOTPDF content here")
            path = tmp.name
        try:
            with self.assertRaises(DocumentUploadError) as ctx:
                _assert_pdf_file(path, "fake.pdf")
            self.assertIn("%PDF", ctx.exception.message)
        finally:
            os.remove(path)

    def test_accept_valid_pdf_header(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"%PDF-1.4\n%demo")
            path = tmp.name
        try:
            _assert_pdf_file(path, "ok.pdf")
        finally:
            os.remove(path)

    def test_reject_file_over_total_limit(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"%PDF-1.4\n")
            tmp.write(b"x" * (MAX_TOTAL_UPLOAD_BYTES + 1))
            path = tmp.name
        try:
            with self.assertRaises(DocumentUploadError) as ctx:
                _assert_pdf_file(path, "huge.pdf")
            self.assertIn("รวมเกิน", ctx.exception.message)
        finally:
            os.remove(path)

    def test_max_total_upload_constant(self):
        self.assertEqual(MAX_TOTAL_UPLOAD_BYTES, 15 * 1024 * 1024)

    def test_duplicate_error_is_conflict(self):
        err = DuplicateDocumentError("Demo Project")
        self.assertEqual(err.status_code, 409)
        self.assertIn("Demo Project", err.message)


if __name__ == "__main__":
    unittest.main()
