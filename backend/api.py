"""HTTP entry for the employee dashboard.

This module only calls the existing sequential crew. It does not talk to Groq
or AnythingLLM, and it does not change how agents retrieve knowledge.
"""

from __future__ import annotations

import logging
import re
import threading
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.config import ConfigError, get_settings
from backend.crew import run_employee_request
from backend.knowledge_catalog import employee_knowledge_catalog
from backend.store import (
    get_request,
    list_activity,
    list_escalations,
    list_requests,
    save_completed_analysis,
    source_usage,
)
from backend.tools.anythingllm_tool import AnythingLLMIntegrationError, get_last_retrieval, query_public_assistant

logger = logging.getLogger("estetik.api")
_analyze_lock = threading.Lock()
_SECRET_RE = re.compile(r"gsk_[A-Za-z0-9_\-]+|sk-[A-Za-z0-9_\-]+|bearer\s+\S+", re.IGNORECASE)

app = FastAPI(title="EstetikAI", docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5174",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class AnalyzeIn(BaseModel):
    employee_request: str = ""
    audience: str = "employee"


class SourceOut(BaseModel):
    title: str
    score: float | None = None


class AnalyzeOut(BaseModel):
    request_type: str
    category: str
    priority: str
    verified_information: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    escalation_required: bool
    reason: str
    knowledge_sources: list[SourceOut] = Field(default_factory=list)
    anythingllm_error: bool = False
    direct_answer: str = ""
    id: str = ""
    created_at: str = ""


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/analyze", response_model=AnalyzeOut)
def analyze(body: AnalyzeIn) -> AnalyzeOut:
    request_text = body.employee_request.strip()
    if not request_text:
        raise HTTPException(
            status_code=400,
            detail="Önce bir mesaj yazın.",
        )
    if body.audience == "client":
        return _client_answer(request_text)
    if not _analyze_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=409,
            detail="Başka bir analiz sürüyor. Lütfen bitmesini bekleyin.",
        )
    started_at = _timestamp()
    try:
        try:
            result = run_employee_request(request_text)
        except ConfigError:
            logger.error("Analysis configuration error")
            raise HTTPException(
                status_code=503,
                detail="Analiz servisi hazır değil. Lütfen yeniden deneyin.",
            ) from None
        except Exception as exc:
            logger.error("Analysis failed: %s", type(exc).__name__)
            raise HTTPException(
                status_code=500,
                detail="Analizi tamamlayamadık. Lütfen yeniden deneyin.",
            ) from None
        public = _public_result(result)
        try:
            saved = save_completed_analysis(
                original_request=request_text,
                result=public.model_dump(),
                started_at=started_at,
                completed_at=_timestamp(),
            )
        except Exception as exc:
            logger.error("Analysis history save failed: %s", type(exc).__name__)
            return public
        public.id = saved["id"]
        public.created_at = saved["created_at"]
        return public
    finally:
        _analyze_lock.release()


@app.get("/api/requests")
def requests_collection() -> list[dict]:
    return _scrub_value(list_requests())  # type: ignore[return-value]


@app.get("/api/requests/{request_id}")
def request_detail(request_id: str) -> dict:
    record = get_request(request_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Talep bulunamadı.")
    return _scrub_value(record)  # type: ignore[return-value]


@app.get("/api/escalations")
def escalations() -> dict:
    return _scrub_value(list_escalations())  # type: ignore[return-value]


@app.get("/api/activity")
def activity() -> list[dict]:
    return _scrub_value(list_activity())  # type: ignore[return-value]


@app.get("/api/knowledge/sources")
def knowledge_sources() -> dict:
    try:
        catalog = employee_knowledge_catalog(source_usage())
    except Exception as exc:
        logger.error("Knowledge catalog failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=500,
            detail="Bilgi kaynakları alınamadı. Lütfen yeniden deneyin.",
        ) from None
    return _scrub_value(catalog)  # type: ignore[return-value]


def _client_answer(request_text: str) -> AnalyzeOut:
    try:
        lookup = query_public_assistant(request_text)
    except AnythingLLMIntegrationError:
        logger.error("Public knowledge query failed")
        return AnalyzeOut(
            request_type="Danışan sorusu",
            category="Klinik",
            priority="Low",
            escalation_required=False,
            reason="",
            anythingllm_error=True,
            direct_answer="Şu an klinik belgelerine ulaşamadım. Bir yetkili size dönüş yapacak.",
        )
    answer = ""
    for snippet in lookup.verified_information:
        if snippet.source == "AnythingLLM textResponse" and snippet.text.strip():
            answer = snippet.text.strip()
            break
    if not answer and lookup.verified_information:
        answer = lookup.verified_information[0].text.strip()
    return AnalyzeOut(
        request_type="Danışan sorusu",
        category="Klinik",
        priority="Low",
        escalation_required=bool(lookup.not_found),
        reason="",
        knowledge_sources=_knowledge_sources(lookup),
        anythingllm_error=False,
        direct_answer=_scrub(answer),
    )


def _public_result(result: dict) -> AnalyzeOut:
    retrieval = get_last_retrieval()
    anythingllm_error = bool(retrieval and retrieval.integration_error)
    if retrieval is None and "AnythingLLM" in str(result.get("reason", "")):
        anythingllm_error = True
    payload = {
        "request_type": _scrub(str(result.get("request_type") or "Unknown")),
        "category": _scrub(str(result.get("category") or "Unspecified")),
        "priority": _scrub(str(result.get("priority") or "Medium")),
        "verified_information": [_scrub(str(item)) for item in result.get("verified_information") or []],
        "missing_information": [_scrub(str(item)) for item in result.get("missing_information") or []],
        "recommended_actions": [_scrub(str(item)) for item in result.get("recommended_actions") or []],
        "escalation_required": bool(result.get("escalation_required")),
        "reason": _scrub(str(result.get("reason") or "")),
        "knowledge_sources": _knowledge_sources(retrieval),
        "anythingllm_error": anythingllm_error,
    }
    return AnalyzeOut.model_validate(payload)


def _knowledge_sources(retrieval: object) -> list[dict[str, object]]:
    if retrieval is None or getattr(retrieval, "integration_error", None):
        return []
    best: dict[str, float | None] = {}
    for source in getattr(retrieval, "sources", []) or []:
        title = str(getattr(source, "title", "") or "").strip()
        if not title:
            continue
        score = getattr(source, "score", None)
        previous = best.get(title)
        if title not in best or (
            isinstance(score, (int, float)) and (previous is None or float(score) > previous)
        ):
            best[title] = float(score) if isinstance(score, (int, float)) else None
    return [{"title": _scrub(title), "score": score} for title, score in best.items()]


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _scrub_value(value: object) -> object:
    if isinstance(value, str):
        return _scrub(value)
    if isinstance(value, list):
        return [_scrub_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _scrub_value(item) for key, item in value.items()}
    return value


def _scrub(text: str) -> str:
    settings = get_settings()
    for secret in (settings.llm_api_key, settings.anythingllm_api_key):
        if secret:
            text = text.replace(secret, "[redacted]")
    return _SECRET_RE.sub("[redacted]", text)
