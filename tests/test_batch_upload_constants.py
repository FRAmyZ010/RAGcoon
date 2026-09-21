"""Batch upload validation (no DB / RAG)."""
import unittest

from app.services.document_service import MAX_BATCH_UPLOAD_FILES, MAX_UPLOAD_BYTES


class BatchUploadConstantsTests(unittest.TestCase):
    def test_max_batch_files(self):
        self.assertEqual(MAX_BATCH_UPLOAD_FILES, 5)

    def test_max_upload_bytes_unchanged(self):
        self.assertEqual(MAX_UPLOAD_BYTES, 25 * 1024 * 1024)


if __name__ == "__main__":
    unittest.main()
