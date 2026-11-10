#!/usr/bin/env bash
# RAGcoon one-click stop for the Docker Compose stack
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

printf '==> Stopping RAGcoon Docker stack\n'
docker compose -p ragcoon down
echo "Stopped. Volumes were kept (postgres/ollama data preserved)."
echo "To wipe volumes too: docker compose -p ragcoon down -v"
