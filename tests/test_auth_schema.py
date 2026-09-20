"""Auth helpers / seed constants (no live DB)."""
import os
import unittest

os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_DB", "test")
os.environ.setdefault("QDRANT_URL", "http://localhost")
os.environ.setdefault("QDRANT_API_KEY", "test")
os.environ.setdefault("JWT_SECRET", "unit-test-jwt-secret-min-32-characters!!")

from app.core.security import ROLE_ADMINISTRATOR, create_access_token, decode_access_token
from app.schemas.auth import Token


class AuthSchemaTests(unittest.TestCase):
    def test_role_constant(self):
        self.assertEqual(ROLE_ADMINISTRATOR, "Administrator")

    def test_token_schema_includes_role_username(self):
        token = Token(
            access_token="abc",
            token_type="bearer",
            role=ROLE_ADMINISTRATOR,
            username="admin",
        )
        self.assertEqual(token.role, "Administrator")
        self.assertEqual(token.username, "admin")

    def test_jwt_roundtrip(self):
        raw = create_access_token({"sub": "admin", "role": ROLE_ADMINISTRATOR})
        payload = decode_access_token(raw)
        self.assertEqual(payload["sub"], "admin")
        self.assertEqual(payload["role"], ROLE_ADMINISTRATOR)


if __name__ == "__main__":
    unittest.main()
