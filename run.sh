#!/bin/bash
cd "$(dirname "$0")"
export USE_POLLING=true
[ -f .venv/bin/activate ] && source .venv/bin/activate
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
