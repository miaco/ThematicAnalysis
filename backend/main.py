"""
Thematic Analysis Agent System — FastAPI Backend
"""

import asyncio
import io
import json
import re
import sys
import os
from datetime import datetime
from typing import AsyncGenerator
from urllib.parse import urlparse

import httpx
import pdfplumber
from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response

# Add backend dir to path for local imports
sys.path.insert(0, os.path.dirname(__file__))

from models.schemas import (
    Session,
    PipelineState,
    CreateSessionRequest,
    SetScreenerRequest,
    CodeReviewRequest,
    POVSelectRequest,
    RecommendationSelectRequest,
)
from storage.session_store import save_session, load_session, list_sessions, delete_session
from agents.orchestrator import run_pipeline, get_progress_queue


app = FastAPI(title="Thematic Analysis Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Session CRUD
# ---------------------------------------------------------------------------

@app.post("/api/sessions", response_model=Session)
async def create_session(req: CreateSessionRequest):
    """Create a new analysis session with a research brief."""
    session = Session(
        research_brief=req.research_brief,
        transcript_source_url=req.transcript_source_url,
    )
    save_session(session)
    return session


@app.get("/api/sessions", response_model=list[Session])
async def get_sessions():
    """List all sessions."""
    return list_sessions()


@app.get("/api/sessions/{session_id}", response_model=Session)
async def get_session(session_id: str):
    """Get a session by ID."""
    session = load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@app.delete("/api/sessions/{session_id}")
async def remove_session(session_id: str):
    """Delete a session."""
    session = load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    delete_session(session_id)
    return {"message": "Session deleted"}


# ---------------------------------------------------------------------------
# Data Upload
# ---------------------------------------------------------------------------

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB per file
ALLOWED_EXTENSIONS = {".txt", ".pdf"}


def _extract_text(filename: str, content_bytes: bytes) -> str:
    """Extract text from an uploaded file based on its extension."""
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".pdf":
        with pdfplumber.open(io.BytesIO(content_bytes)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        text = "\n\n".join(pages).strip()
        if not text:
            raise ValueError(f"No extractable text found in {filename}")
        return text
    # Default: treat as plain text
    try:
        return content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return content_bytes.decode("latin-1", errors="replace")


@app.post("/api/sessions/{session_id}/transcripts")
async def upload_transcripts(session_id: str, files: list[UploadFile] = File(...)):
    """Upload transcript files (multipart). Accepts .txt and .pdf files."""
    session = load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.state not in (PipelineState.IDLE, PipelineState.PROCESSING_TRANSCRIPTS):
        raise HTTPException(status_code=400, detail="Cannot upload transcripts in current state")

    errors = []
    added = []
    for upload in files:
        ext = os.path.splitext(upload.filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            errors.append(f"{upload.filename}: unsupported file type '{ext}'. Use .txt or .pdf.")
            continue

        content_bytes = await upload.read()
        if len(content_bytes) > MAX_FILE_SIZE:
            errors.append(f"{upload.filename}: exceeds 10 MB size limit.")
            continue
        if len(content_bytes) == 0:
            errors.append(f"{upload.filename}: file is empty.")
            continue

        try:
            content = _extract_text(upload.filename, content_bytes)
        except Exception as exc:
            errors.append(f"{upload.filename}: {exc}")
            continue

        session.transcripts[upload.filename] = content
        added.append(upload.filename)

    if not added and errors:
        raise HTTPException(status_code=400, detail="No files could be processed. " + " | ".join(errors))

    save_session(session)
    result: dict = {"message": f"Uploaded {len(added)} transcript(s)", "files": list(session.transcripts.keys())}
    if errors:
        result["warnings"] = errors
    return result


@app.post("/api/sessions/{session_id}/transcripts/fetch")
async def fetch_transcript_from_url(session_id: str, payload: dict):
    """Fetch a transcript from a public URL and add it to the session."""
    session = load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.state not in (PipelineState.IDLE, PipelineState.PROCESSING_TRANSCRIPTS):
        raise HTTPException(status_code=400, detail="Cannot add transcripts in current state")

    url = (payload.get("url") or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="URL must use http or https")

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=400, detail=f"Remote server returned {exc.response.status_code}")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {exc}")

    content_bytes = resp.content
    if len(content_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Fetched file exceeds 10 MB size limit")
    if len(content_bytes) == 0:
        raise HTTPException(status_code=400, detail="Fetched file is empty")

    # Derive a filename from the URL path
    path_tail = parsed.path.rstrip("/").split("/")[-1] or "transcript"
    filename = re.sub(r'[^\w.\-]', '_', path_tail)
    if not os.path.splitext(filename)[1]:
        content_type = resp.headers.get("content-type", "")
        if "pdf" in content_type:
            filename += ".pdf"
        else:
            filename += ".txt"

    try:
        content = _extract_text(filename, content_bytes)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not extract text: {exc}")

    session.transcripts[filename] = content
    save_session(session)
    return {"message": f"Fetched and added '{filename}'", "files": list(session.transcripts.keys())}


@app.post("/api/sessions/{session_id}/screener")
async def set_screener(session_id: str, req: SetScreenerRequest):
    """Set the screener questions for demographic grouping."""
    session = load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.screener_questions = req.screener_questions
    save_session(session)
    return {"message": f"Screener questions set ({len(req.screener_questions)} questions)"}


# ---------------------------------------------------------------------------
# Pipeline Control
# ---------------------------------------------------------------------------

@app.post("/api/sessions/{session_id}/run")
async def run_session_pipeline(session_id: str, background_tasks: BackgroundTasks):
    """Start or continue the pipeline. Runs asynchronously."""
    session = load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.state in (PipelineState.PROCESSING_TRANSCRIPTS,
                          PipelineState.PROCESSING_THEMES,
                          PipelineState.PROCESSING_RECOMMENDATIONS,
                          PipelineState.WRITING_REPORT):
        raise HTTPException(status_code=400, detail="Pipeline is already running")

    if session.state == PipelineState.COMPLETE:
        raise HTTPException(status_code=400, detail="Pipeline is already complete")

    # Allow retrying from an error state — reset to the last human gate or idle
    if session.state == PipelineState.ERROR:
        session.state = PipelineState.IDLE
        session.error = None
        save_session(session)

    if session.state == PipelineState.IDLE and not session.transcripts:
        raise HTTPException(status_code=400, detail="No transcripts uploaded. Please upload transcripts first.")

    # Run pipeline as a background task
    background_tasks.add_task(_run_pipeline_task, session_id)
    return {"message": "Pipeline started", "state": session.state}


async def _run_pipeline_task(session_id: str):
    """Wrapper to run pipeline in background."""
    try:
        await run_pipeline(session_id)
    except Exception as e:
        # Error is already handled in orchestrator
        pass


# ---------------------------------------------------------------------------
# SSE Progress Stream
# ---------------------------------------------------------------------------

@app.get("/api/sessions/{session_id}/progress")
async def progress_stream(session_id: str):
    """Server-Sent Events stream for pipeline progress updates."""
    session = load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    async def event_generator() -> AsyncGenerator[str, None]:
        queue = get_progress_queue(session_id)
        # Send existing log entries first
        current = load_session(session_id)
        if current:
            for entry in current.progress_log:
                data = json.dumps(entry)
                yield f"data: {data}\n\n"

        # Stream new events
        timeout_count = 0
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                data = json.dumps(event)
                yield f"data: {data}\n\n"

                # Check if pipeline is done
                if event.get("stage") in ("complete", "error", "awaiting_code_review",
                                           "awaiting_pov_selection", "awaiting_recommendation_selection"):
                    # Send a final "done" marker then stop
                    yield f"data: {json.dumps({'stage': 'stream_end', 'message': 'Stream complete'})}\n\n"
                    break

                timeout_count = 0
            except asyncio.TimeoutError:
                # Send keepalive
                yield f": keepalive\n\n"
                timeout_count += 1
                if timeout_count > 6:  # 3 minutes of inactivity
                    break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ---------------------------------------------------------------------------
# Human Gate Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/sessions/{session_id}/codes/review")
async def submit_code_review(session_id: str, req: CodeReviewRequest, background_tasks: BackgroundTasks):
    """
    Human gate 1: Submit reviewed/edited codes.
    After this, the pipeline continues to theme generation.
    """
    session = load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.state != PipelineState.AWAITING_CODE_REVIEW:
        raise HTTPException(
            status_code=400,
            detail=f"Session is not awaiting code review (current state: {session.state})"
        )

    # Update codes with the reviewed versions
    session.codes = req.codes
    session.progress_log.append({
        "timestamp": datetime.utcnow().isoformat(),
        "stage": "code_review",
        "message": f"Human reviewed and submitted {len(req.codes)} codes",
    })

    save_session(session)

    # Continue pipeline
    background_tasks.add_task(_run_pipeline_task, session_id)
    return {"message": "Code review submitted. Pipeline continuing to theme generation.", "code_count": len(req.codes)}


@app.post("/api/sessions/{session_id}/pov/select")
async def select_pov(session_id: str, req: POVSelectRequest, background_tasks: BackgroundTasks):
    """
    Human gate 2: Select a POV by ID.
    After this, the pipeline continues to recommendation generation.
    """
    session = load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.state != PipelineState.AWAITING_POV_SELECTION:
        raise HTTPException(
            status_code=400,
            detail=f"Session is not awaiting POV selection (current state: {session.state})"
        )

    # Find the selected POV
    selected = next((p for p in session.povs if p.id == req.pov_id), None)
    if not selected:
        raise HTTPException(status_code=404, detail=f"POV with id '{req.pov_id}' not found")

    session.selected_pov = selected
    session.progress_log.append({
        "timestamp": datetime.utcnow().isoformat(),
        "stage": "pov_selection",
        "message": f"Human selected POV: '{selected.title}'",
    })

    save_session(session)

    # Continue pipeline
    background_tasks.add_task(_run_pipeline_task, session_id)
    return {"message": f"POV '{selected.title}' selected. Pipeline continuing to recommendation generation."}


@app.post("/api/sessions/{session_id}/recommendations/select")
async def select_recommendations(
    session_id: str, req: RecommendationSelectRequest, background_tasks: BackgroundTasks
):
    """
    Human gate 3: Select which recommendations to include in the final report.
    After this, the pipeline continues to report writing.
    """
    session = load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.state != PipelineState.AWAITING_RECOMMENDATION_SELECTION:
        raise HTTPException(
            status_code=400,
            detail=f"Session is not awaiting recommendation selection (current state: {session.state})"
        )

    selected_set = set(req.selected_ids)
    for rec in session.recommendations:
        rec.selected = rec.id in selected_set

    selected_count = sum(1 for r in session.recommendations if r.selected)
    session.progress_log.append({
        "timestamp": datetime.utcnow().isoformat(),
        "stage": "recommendation_selection",
        "message": f"Human selected {selected_count} of {len(session.recommendations)} recommendations",
    })

    save_session(session)

    # Continue pipeline
    background_tasks.add_task(_run_pipeline_task, session_id)
    return {"message": f"{selected_count} recommendations selected. Pipeline continuing to report writing."}


# ---------------------------------------------------------------------------
# Report Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/sessions/{session_id}/report")
async def get_report(session_id: str):
    """Get the final report as markdown text."""
    session = load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.report:
        raise HTTPException(status_code=404, detail="Report not yet generated")
    return {"report": session.report}


@app.get("/api/sessions/{session_id}/report/download")
async def download_report(session_id: str):
    """Download the final report as a .md file."""
    session = load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.report:
        raise HTTPException(status_code=404, detail="Report not yet generated")

    filename = f"thematic_analysis_report_{session_id[:8]}.md"
    return Response(
        content=session.report,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}
