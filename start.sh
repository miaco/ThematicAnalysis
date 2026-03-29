#!/bin/bash
set -e

echo "========================================"
echo "  Thematic Analysis Agent System"
echo "========================================"
echo ""

# Check for ANTHROPIC_API_KEY
if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo "WARNING: ANTHROPIC_API_KEY environment variable is not set."
  echo "The backend will fail when making AI calls."
  echo "Set it with: export ANTHROPIC_API_KEY=your_key_here"
  echo ""
fi

# Start backend
echo "Starting backend (FastAPI on port 8000)..."
cd "$(dirname "$0")/backend"
pip install -r requirements.txt -q
uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Give backend a moment to start
sleep 2

# Start frontend
echo ""
echo "Starting frontend (Vite on port 5173)..."
cd "$(dirname "$0")/frontend"
npm install --silent
npm run dev &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"

echo ""
echo "========================================"
echo "  Services running:"
echo "  Backend:  http://localhost:8000"
echo "  Frontend: http://localhost:5173"
echo "  API Docs: http://localhost:8000/docs"
echo "========================================"
echo ""
echo "Press Ctrl+C to stop all services."

# Cleanup on exit
cleanup() {
  echo ""
  echo "Stopping services..."
  kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
  echo "Done."
}
trap cleanup EXIT INT TERM

wait
