"""Feedback submission rules. No database and no file write on the reject path."""
import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_DB", "test")
os.environ.setdefault("QDRANT_URL", "http://localhost")
os.environ.setdefault("QDRANT_API_KEY", "test")
os.environ.setdefault("JWT_SECRET", "unit-test-jwt-secret-min-32-characters!!")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from pydantic import ValidationError

from app.schemas.feedback import FeedbackStatusUpdate
from app.services.feedback_service import (
    MAX_ATTACHMENT_BYTES,
    FeedbackError,
    save_attachment,
    validate_submission,
)


class FeedbackContractTests(unittest.TestCase):
    def test_accepts_form_fields(self):
        fields = validate_submission(
            name=" Ann ",
            rating=4,
            feedback_type="Others",
            comment=" slow search ",
        )
        self.assertEqual(fields["submitter_name"], "Ann")
        self.assertEqual(fields["feedback_type"], "Others")
        self.assertEqual(fields["comment"], "slow search")

    def test_rejects_unknown_type_and_empty_comment(self):
        with self.assertRaises(FeedbackError):
            validate_submission(name="Ann", rating=5, feedback_type="Other", comment="hi")
        with self.assertRaises(FeedbackError):
            validate_submission(name="Ann", rating=5, feedback_type="Bug", comment="  ")

    def test_rejects_attachment_over_10mb(self):
        with self.assertRaises(FeedbackError):
            save_attachment("note.txt", b"x" * (MAX_ATTACHMENT_BYTES + 1))

    def test_status_update_rejects_unknown_status(self):
        self.assertEqual(FeedbackStatusUpdate(status="In Progress").status, "In Progress")
        with self.assertRaises(ValidationError):
            FeedbackStatusUpdate(status="Closed")


if __name__ == "__main__":
    unittest.main()
