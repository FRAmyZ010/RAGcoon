"""Batch upload validation constants (no DB / RAG)."""
import unittest

from app.services.document_service import MAX_TOTAL_UPLOAD_BYTES, MAX_TOTAL_UPLOAD_MB


class BatchUploadConstantsTests(unittest.TestCase):
    def test_max_total_upload_bytes(self):
        self.assertEqual(MAX_TOTAL_UPLOAD_BYTES, 100 * 1024 * 1024)

    def test_max_total_upload_mb(self):
        self.assertEqual(MAX_TOTAL_UPLOAD_MB, 100)


if __name__ == "__main__":
    unittest.main()
