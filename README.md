# Thematic Analysis

Thematic Analysis is a local full-stack application for running an AI-assisted qualitative research workflow over interview transcripts. It combines a FastAPI backend, a React/Vite frontend, and a staged agent pipeline that pauses at key human review steps before producing a final markdown report.

## What It Does

- Creates analysis sessions from a research brief
- Uploads transcript files (.txt and .pdf) into a session
- Fetches transcripts from public URLs (Google Drive, Dropbox, SharePoint, etc.)
- Extracts quotes and generates open codes
- Evaluates codes on quality metrics (coverage, actionability, distinctiveness, relevance)
- Pauses for human code review before continuing
- Generates themes and candidate points of view
- Evaluates themes on the same quality metrics
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
- Persistence: SQLite (WAL mode)
- PDF parsing: pdfplumber
- HTTP client: httpx (for URL transcript fetching)
- Realtime progress: Server-Sent Events (SSE)

## Project Structure

```text
.
├── backend/
│   ├── agents/           # Pipeline stages: transcript, coding, evaluation, themes, POV, report
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
4. Optionally add a transcript source link (a public URL pointing to transcript files).
5. Optionally add screener or demographic questions, one per line.
6. Upload transcript files (.txt or .pdf, max 10 MB each).
7. Start the pipeline.
8. Review and edit generated codes when the workflow pauses. Each code displays quality scores on four criteria: coverage, actionability, distinctiveness, and relevance (1–5 scale).
9. Select the preferred analytical POV. A theme quality summary card shows aggregate evaluation scores.
10. Select which recommendations should appear in the final report.
11. Download the completed markdown report.

If the pipeline encounters an error, you can retry from the session view — the app will reset and re-run from the last checkpoint.

## Data Storage

Session data is stored in a local SQLite database at `backend/thematic_analysis.db` using WAL mode for safe concurrent reads. Each session record includes pipeline state, uploaded transcripts, extracted quotes, codes, themes, POVs, recommendations, validation results, and the generated report.

The database is local working data and is excluded from version control via `.gitignore`.

## API Overview

Core endpoints include:

- `POST /api/sessions` to create a session
- `GET /api/sessions` to list sessions
- `GET /api/sessions/{session_id}` to fetch a session
- `DELETE /api/sessions/{session_id}` to delete a session
- `POST /api/sessions/{session_id}/transcripts` to upload transcripts (.txt, .pdf)
- `POST /api/sessions/{session_id}/transcripts/fetch` to fetch a transcript from a public URL
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

- The frontend API base URL defaults to `http://localhost:8000` and can be overridden by setting the `VITE_API_URL` environment variable before building or starting the frontend.
- CORS is enabled for local frontend development on port `5173`.
- Progress updates are streamed from the backend over SSE during active pipeline stages.
- Uploaded files are validated for type (.txt, .pdf), size (10 MB max), and content before processing.
- PDF files are parsed with pdfplumber; text is extracted page-by-page.
- If the pipeline errors out, re-running it will automatically retry from the beginning.

## Evaluation Metrics

Inspired by the [TAMA framework](https://github.com/Charlie-Yi-SJ/TAMA), the pipeline includes an evaluation agent that scores codes and themes on four criteria:

| Criterion | What it measures |
|---|---|
| **Coverage** | How well the item captures important patterns in the data |
| **Actionability** | Whether it encapsulates a single, clear concept |
| **Distinctiveness** | How clearly it is differentiated from other items in the set |
| **Relevance** | How accurately it reflects participant data and the research brief |

Each item receives a score from 1.0 to 5.0 on each criterion. Scores are displayed in the UI during code review (per-code badges and breakdowns) and POV selection (aggregate theme quality card). Unlike TAMA's automated refinement loop, these scores inform the human reviewer rather than driving autonomous iteration — the researcher makes the final call.

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