#!/bin/sh

set -e

echo "Waiting for PostgreSQL database to start..."
# รัน Alembic Migration เพื่ออัปเดต Schema DB ล่าสุด
alembic upgrade head

echo "Database migrations completed successfully."

# เริ่มรัน FastAPI Server
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload