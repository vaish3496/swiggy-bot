#!/bin/bash
# Start all services for the Swiggy Flat Bot

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Starting FastAPI app..."
cd "$SCRIPT_DIR"
uvicorn app.main:app --host 0.0.0.0 --port 8000
