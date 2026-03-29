# Thematic Analysis

Thematic Analysis is a local full-stack application for running an AI-assisted qualitative research workflow over interview transcripts. It combines a FastAPI backend, a React/Vite frontend, and a staged agent pipeline that pauses at key human review steps before producing a final markdown report.

## What It Does

- Creates analysis sessions from a research brief
- Uploads transcript files into a session
- Extracts quotes and generates open codes
- Pauses for human code review before continuing
- Generates themes and candidate points of view
- Pauses for POV selection
- Generates recommendations tied to the selected POV
- Pauses for recommendation selection
- Writes a final markdown report and supports download

## Workflow

The backend pipeline moves through these states:

1. `idle`
2. `processing_transcripts`
3. `awaiting_code_review`
4. `processing_themes`
5. `awaiting_pov_selection`
6. `processing_recommendations`
7. `awaiting_recommendation_selection`
8. `writing_report`
9. `complete`

The application is intentionally human-in-the-loop. It does not run straight through to the report without intervention.

## Tech Stack

- Backend: FastAPI, Pydantic, Uvicorn
- Frontend: React, TypeScript, Vite, Tailwind CSS
- AI integration: Anthropic API
- Persistence: JSON session files stored on disk
- Realtime progress: Server-Sent Events (SSE)

## Project Structure

```text
.
├── backend/
│   ├── agents/           # Pipeline stages: transcript, coding, themes, POV, report
│   ├── models/           # Pydantic schemas and pipeline state models
│   ├── storage/          # Session persistence
│   ├── main.py           # FastAPI app and API routes
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/          # API client and SSE helper
│   │   └── components/   # UI for upload, progress, review, selection, report
│   └── package.json
├── start.sh              # Starts backend and frontend locally
└── README.md
```

## Prerequisites

- Python 3.10+
- Node.js 18+
- npm
- An Anthropic API key

## Environment

Set your Anthropic API key before running the app:

```bash
export ANTHROPIC_API_KEY=your_key_here
```

Without this variable, the backend starts but agent calls will fail when the pipeline reaches model-backed stages.

## Quick Start

From the repository root:

```bash
chmod +x start.sh
./start.sh
```

That script will:

- install backend Python dependencies
- start FastAPI on `http://localhost:8000`
- install frontend dependencies
- start Vite on `http://localhost:5173`

Useful URLs:

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

## Manual Development Setup

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## How To Use

1. Open the frontend in your browser.
2. Create a new analysis session.
3. Enter a research brief describing the study objective and context.
4. Optionally add screener or demographic questions, one per line.
5. Upload transcript files.
6. Start the pipeline.
7. Review and edit generated codes when the workflow pauses.
8. Select the preferred analytical POV.
9. Select which recommendations should appear in the final report.
10. Download the completed markdown report.

## Data Storage

Session data is stored locally as JSON files under `backend/sessions/`. Each session includes pipeline state, uploaded transcripts, extracted quotes, codes, themes, POVs, recommendations, validation results, and the generated report.

These files are local working data and are not intended for production-grade storage.

## API Overview

Core endpoints include:

- `POST /api/sessions` to create a session
- `GET /api/sessions` to list sessions
- `GET /api/sessions/{session_id}` to fetch a session
- `DELETE /api/sessions/{session_id}` to delete a session
- `POST /api/sessions/{session_id}/transcripts` to upload transcripts
- `POST /api/sessions/{session_id}/screener` to set screener questions
- `POST /api/sessions/{session_id}/run` to start or continue the pipeline
- `GET /api/sessions/{session_id}/progress` for SSE progress streaming
- `POST /api/sessions/{session_id}/codes/review` to submit reviewed codes
- `POST /api/sessions/{session_id}/pov/select` to select a POV
- `POST /api/sessions/{session_id}/recommendations/select` to select recommendations
- `GET /api/sessions/{session_id}/report` to fetch the final report
- `GET /api/sessions/{session_id}/report/download` to download the report as markdown
- `GET /api/health` for health checks

## Notes

- The frontend is configured to talk to `http://localhost:8000`.
- CORS is enabled for local frontend development on port `5173`.
- Progress updates are streamed from the backend over SSE during active pipeline stages.
- The current implementation is optimized for local use and experimentation rather than deployment hardening.

## Development Commands

Frontend build:

```bash
cd frontend
npm run build
```

Backend run:

```bash
cd backend
uvicorn main:app --reload --port 8000
```

## License

No license file is currently included in this repository.