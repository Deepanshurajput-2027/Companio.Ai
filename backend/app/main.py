import os
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

from .models import ChatRequest, MatchRequest
from .services import extract_document_text, load_profile, match_job_description, stream_chat

load_dotenv()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    load_profile()
    yield


app = FastAPI(title="Companio.ai API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_rate_limit_state: dict[tuple[str, str], list[float]] = {}
RESUME_PATH = (
    Path(__file__).parent.parent / "knowledgebase" / "resume" / "deepanshu_rajput_resume_v1.pdf"
)


def _rate_limit(request: Request, bucket: str, limit: int) -> None:
    now = time.monotonic()
    key = (request.client.host if request.client else "unknown", bucket)
    timestamps = [timestamp for timestamp in _rate_limit_state.get(key, []) if now - timestamp < 60]
    if len(timestamps) >= limit:
        retry_after = max(1, int(60 - (now - timestamps[0])))
        raise HTTPException(
            status_code=429,
            detail=f"Too many {bucket} requests. Try again in about {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )
    timestamps.append(now)
    _rate_limit_state[key] = timestamps


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/profile")
def profile() -> dict:
    return load_profile().model_dump()


@app.get("/api/resume")
def resume() -> FileResponse:
    if not RESUME_PATH.is_file():
        raise HTTPException(status_code=404, detail="Resume file is not available.")
    return FileResponse(
        RESUME_PATH,
        media_type="application/pdf",
        filename="Deepanshu_Rajput_Resume.pdf",
    )


@app.post("/api/chat")
def chat(request: Request, payload: ChatRequest) -> StreamingResponse:
    _rate_limit(request, "chat", int(os.getenv("CHAT_RATE_LIMIT_PER_MINUTE", "10")))
    try:
        chunks = stream_chat(payload.message, payload.history, payload.job_description)
        return StreamingResponse(chunks, media_type="text/plain; charset=utf-8")
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.post("/api/match", response_model=None)
def match(request: Request, payload: MatchRequest):
    _rate_limit(request, "match", int(os.getenv("MATCH_RATE_LIMIT_PER_MINUTE", "5")))
    try:
        return match_job_description(payload.job_description)
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(
            status_code=502, detail="The model returned invalid match data."
        ) from error


@app.post("/api/match/upload", response_model=None)
async def match_upload(request: Request, file: Annotated[UploadFile, File(...)]):
    _rate_limit(request, "match", int(os.getenv("MATCH_RATE_LIMIT_PER_MINUTE", "5")))
    try:
        content = await file.read()
        job_description = extract_document_text(file.filename or "", content)
        if len(job_description.strip()) < 20:
            raise HTTPException(
                status_code=400, detail="The uploaded file contains too little text."
            )
        return match_job_description(job_description)
    except HTTPException:
        raise
    except (RuntimeError, ValueError) as error:
        status = 503 if isinstance(error, RuntimeError) else 400
        raise HTTPException(status_code=status, detail=str(error)) from error
