"""AnythingLLM Employee Knowledge adapter.

Live mode calls the confirmed Developer API. The API key is read from the
environment and is never written into source code or logs.
"""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import quote

# Settings load first so CREWAI_DISABLE_TELEMETRY is set before CrewAI imports.
from backend.config import get_settings
from backend.models.schemas import (
    KnowledgeLookup,
    KnowledgeSnippet,
    KnowledgeSource,
    restricted_topics_in,
)

import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# Stand-in excerpts only. They are not copies of the uploaded clinic PDFs.
# They state routing rules and explicitly withhold dynamic commercial and clinical facts.
MOCK_DOCUMENTS: list[dict[str, Any]] = [
    {
        "id": "employee_ai_policy",
        "title": "Employee AI Policy (mock)",
        "keywords": ("asistan", "policy", "uydur", "bilgi tabanı", "knowledge"),
        "text": (
            "Çalışan asistanı yalnızca Employee Knowledge içeriğini aktarır. "
            "Bilgi tabanında olmayan şirket prosedürünü tamamlamaz. "
            "Teşhis koymaz, kişisel tedavi önermez, tıbbi uygunluk belirlemez ve sonuç garantisi vermez. "
            "Fiyat, randevu, hekim, çalışan, departman, paket, konaklama ve transfer uydurulmaz."
        ),
    },
    {
        "id": "international_operations",
        "title": "International Operations (mock)",
        "keywords": ("almanya", "yurt", "uluslar", "international", "ülke", "ulke", "ziyaretçi", "ziyaretci"),
        "text": (
            "Yurt dışından gelen ziyaretçi talebi international operations akışına not edilir. "
            "Ülke ve talep konusu kayda geçirilir. "
            "Bu notta ülke bazlı fiyat, tarih, hekim veya hizmet taahhüdü yoktur; "
            "bunlar insan onayı olmadan cevaplanmaz."
        ),
    },
    {
        "id": "lead_management",
        "title": "Lead Management (mock)",
        "keywords": ("lead", "talep", "ziyaretçi", "ziyaretci", "kayıt", "kayit"),
        "text": (
            "Yeni ziyaretçi talebi bir lead özeti olarak işlenir. "
            "Talep konusu ve eksik iletişim bilgisi not edilir. "
            "Lead sistemi teyit edilmeden talebin işlendiği, ödemenin alındığı veya randevunun verildiği söylenmez."
        ),
    },
    {
        "id": "escalation_ownership",
        "title": "Escalation and Ownership (mock)",
        "keywords": ("escalation", "eskalasyon", "onay", "ownership", "sahiplik"),
        "text": (
            "Fiyat, randevu, hekim veya çalışan adı, departman adı, paket, konaklama, transfer, "
            "tıbbi uygunluk ya da bilgi tabanında olmayan prosedür sorularında talep insana bırakılır. "
            "Bu not belirli bir kişi veya departman adı içermez."
        ),
    },
    {
        "id": "internal_operations",
        "title": "Internal Operations (mock)",
        "keywords": ("operasyon", "çalışan", "calisan", "adım", "adim", "prosedür", "prosedur"),
        "text": (
            "Çalışan talebi önce sınıflandırılır, sonra yalnızca doğrulanmış kurumsal nota göre sonraki adım yazılır. "
            "Gerçekleşmemiş bir işlem yapılmış gibi gösterilmez."
        ),
    },
    {
        "id": "hair_transplant_routing",
        "title": "Hair Transplant Routing (mock)",
        "keywords": ("saç", "sac", "hair", "ekim", "transplant"),
        "text": (
            "Saç ekimiyle ilgili ziyaretçi talebi Hair Transplant kategorisinde operasyon akışına alınır. "
            "Bu not fiyat, paket içeriği, hekim, konaklama, transfer, uygunluk kriteri veya randevu tarihi içermez."
        ),
    },
]

_last_retrieval: KnowledgeLookup | None = None

_PRICE_RE = re.compile(
    r"(?:€|\$|₺)\s*\d[\d.,]*|\b\d[\d.,]*\s*(?:€|eur|euro|usd|tl|₺|\$|dolar)\b",
    re.IGNORECASE,
)
_DATE_RE = re.compile(r"\b\d{1,2}[./]\d{1,2}[./]\d{2,4}\b")
_DOCTOR_RE = re.compile(r"\b(?:Dr\.?|Doktor|Doctor)\s+[A-ZÇĞİÖŞÜ][\wçğıöşüÇĞİÖŞÜ'-]+")
_MEDICAL_DECISION_RE = re.compile(
    r"tıbbi olarak uygun|operasyona uygun|uygun bir aday|uygun değildir|uygun degildir|"
    r"eligible for|not eligible",
    re.IGNORECASE,
)
_LIVE_TIMEOUT_SECONDS = 180


class AnythingLLMIntegrationError(RuntimeError):
    """Live AnythingLLM call failed. Callers must not replace this with mock data."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        endpoint: str = "",
        text_response: str | None = None,
        sources: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.endpoint = endpoint
        self.text_response = text_response
        self.sources = sources or []


class AnythingLLMQueryInput(BaseModel):
    """Question sent to the Employee Knowledge workspace."""

    question: str = Field(..., description="What should be looked up in company documents.")


class AnythingLLMClient:
    """Talks to AnythingLLM, or to the local mock corpus when MOCK_MODE is true."""

    def __init__(self) -> None:
        self.last_status_code: int | None = None
        self.last_endpoint: str = ""
        self.last_text_response: str | None = None
        self.last_sources: list[dict[str, Any]] = []

    def query(self, question: str) -> KnowledgeLookup:
        cleaned = question.strip()
        if not cleaned:
            raise ValueError("AnythingLLM sorgusu boş olamaz.")
        settings = get_settings()
        if settings.mock_mode:
            return self._query_mock(cleaned)
        return self._query_live(cleaned)

    def _query_mock(self, question: str) -> KnowledgeLookup:
        settings = get_settings()
        folded = question.casefold()
        topics = restricted_topics_in(question)
        ranked: list[tuple[int, dict[str, Any]]] = []

        for document in MOCK_DOCUMENTS:
            score = 0
            for keyword in document["keywords"]:
                if keyword.casefold() in folded:
                    score += 2
            for token in _tokens(question):
                if token in document["text"].casefold():
                    score += 1
            if document["id"] == "employee_ai_policy" and topics:
                score += 5
            if document["id"] == "escalation_ownership" and topics:
                score += 4
            if score > 0:
                ranked.append((score, document))

        ranked.sort(key=lambda item: item[0], reverse=True)
        snippets = [
            KnowledgeSnippet(source=document["title"], text=document["text"])
            for _, document in ranked[:4]
        ]
        workspace = settings.anythingllm_employee_workspace_slug or "EstetikAI – Employee Knowledge"
        return KnowledgeLookup(
            mode="mock",
            workspace=workspace,
            question=question,
            verified_information=snippets,
            not_found=topics,
        )

    def _query_live(self, question: str, workspace_slug: str | None = None) -> KnowledgeLookup:
        """POST the question to an AnythingLLM workspace in query mode."""
        settings = get_settings()
        missing = settings.missing_anythingllm()
        if missing:
            raise AnythingLLMIntegrationError(
                "MOCK_MODE=false ancak şu değişkenler boş: " + ", ".join(missing)
            )

        slug = quote(workspace_slug or settings.anythingllm_employee_workspace_slug, safe="")
        endpoint = f"{settings.anythingllm_base_url}/api/v1/workspace/{slug}/chat"
        self.last_endpoint = endpoint
        api_key = settings.anythingllm_api_key
        if api_key.lower().startswith("bearer "):
            api_key = api_key[7:].strip()

        try:
            response = requests.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json={"message": question, "mode": "query", "reset": True},
                timeout=_LIVE_TIMEOUT_SECONDS,
            )
        except requests.Timeout as exc:
            raise AnythingLLMIntegrationError(
                "AnythingLLM zaman aşımına uğradı.",
                endpoint=endpoint,
            ) from exc
        except requests.ConnectionError as exc:
            raise AnythingLLMIntegrationError(
                "AnythingLLM bağlantısı kurulamadı. Servis kapalı olabilir.",
                endpoint=endpoint,
            ) from exc
        except requests.RequestException as exc:
            raise AnythingLLMIntegrationError(
                "AnythingLLM isteği tamamlanamadı.",
                endpoint=endpoint,
            ) from exc

        self.last_status_code = response.status_code
        if response.status_code in {401, 403}:
            raise AnythingLLMIntegrationError(
                f"AnythingLLM yetki hatası döndü (HTTP {response.status_code}).",
                status_code=response.status_code,
                endpoint=endpoint,
            )
        if response.status_code == 404:
            raise AnythingLLMIntegrationError(
                "AnythingLLM workspace bulunamadı (HTTP 404).",
                status_code=response.status_code,
                endpoint=endpoint,
            )
        if response.status_code >= 400:
            raise AnythingLLMIntegrationError(
                f"AnythingLLM HTTP {response.status_code} döndü.",
                status_code=response.status_code,
                endpoint=endpoint,
            )

        try:
            body = response.json()
        except ValueError as exc:
            raise AnythingLLMIntegrationError(
                "AnythingLLM geçersiz JSON döndü.",
                status_code=response.status_code,
                endpoint=endpoint,
            ) from exc
        if not isinstance(body, dict):
            raise AnythingLLMIntegrationError(
                "AnythingLLM JSON nesnesi döndürmedi.",
                status_code=response.status_code,
                endpoint=endpoint,
            )

        text_response = body.get("textResponse")
        sources = _parse_sources(body.get("sources"))
        source_payload = [source.model_dump() for source in sources]
        self.last_sources = source_payload
        self.last_text_response = text_response.strip() if isinstance(text_response, str) else None
        if not isinstance(text_response, str) or not text_response.strip():
            raise AnythingLLMIntegrationError(
                "AnythingLLM textResponse boş döndü.",
                status_code=response.status_code,
                endpoint=endpoint,
                text_response=self.last_text_response,
                sources=source_payload,
            )

        source_evidence = "\n".join(source.text for source in sources if source.text.strip())
        snippets = [
            KnowledgeSnippet(source=source.title or "AnythingLLM source", text=source.text.strip())
            for source in sources
            if source.text.strip()
        ]
        response_text = text_response.strip()
        if not source_evidence or not _text_adds_unsupported_specifics(response_text, source_evidence):
            snippets.insert(
                0,
                KnowledgeSnippet(source="AnythingLLM textResponse", text=response_text),
            )
        evidence = source_evidence or response_text
        return KnowledgeLookup(
            mode="live",
            workspace=workspace_slug or settings.anythingllm_employee_workspace_slug,
            question=question,
            verified_information=snippets,
            not_found=_unverified_topics(question, evidence),
            sources=sources,
        )


def reset_last_retrieval() -> None:
    global _last_retrieval
    _last_retrieval = None


def get_last_retrieval() -> KnowledgeLookup | None:
    return _last_retrieval


def _remember(lookup: KnowledgeLookup) -> None:
    global _last_retrieval
    _last_retrieval = lookup


def _tokens(text: str) -> set[str]:
    cleaned = "".join(character if character.isalnum() else " " for character in text.casefold())
    return {token for token in cleaned.split() if len(token) >= 4}


def _parse_sources(raw: Any) -> list[KnowledgeSource]:
    if not isinstance(raw, list):
        return []
    sources: list[KnowledgeSource] = []
    for item in raw:
        if isinstance(item, str):
            text = item.strip()
            if text:
                sources.append(KnowledgeSource(text=text))
            continue
        if not isinstance(item, dict):
            continue
        text = item.get("text") or item.get("chunk") or ""
        title = item.get("title") or item.get("docSource") or ""
        score = item.get("score")
        sources.append(
            KnowledgeSource(
                title=str(title).strip(),
                text=str(text).strip(),
                score=float(score) if isinstance(score, (int, float)) else None,
            )
        )
    return sources


def _unverified_topics(question: str, evidence: str) -> list[str]:
    """Restricted topics in the question that the workspace text does not actually answer."""
    missing: list[str] = []
    comparable = _without_document_metadata(evidence)
    for topic in restricted_topics_in(question):
        if not _topic_has_concrete_fact(topic, comparable):
            missing.append(topic)
    return missing


def _without_document_metadata(evidence: str) -> str:
    """Ignore AnythingLLM file metadata so a publish date is not an appointment."""
    kept: list[str] = []
    for line in evidence.splitlines():
        folded = line.strip().casefold()
        if folded in {"<document_metadata>", "</document_metadata>"}:
            continue
        if folded.startswith("sourcedocument:") or folded.startswith("published:"):
            continue
        kept.append(line)
    return "\n".join(kept)


def _topic_has_concrete_fact(topic: str, evidence: str) -> bool:
    if topic == "price":
        return _PRICE_RE.search(evidence) is not None
    if topic == "appointment_date":
        return _DATE_RE.search(evidence) is not None
    if topic == "doctor_name":
        return _DOCTOR_RE.search(evidence) is not None
    if topic == "medical_suitability":
        return _MEDICAL_DECISION_RE.search(evidence) is not None
    return False


def _text_adds_unsupported_specifics(text: str, source_blob: str) -> bool:
    folded_sources = source_blob.casefold()
    for pattern in (_PRICE_RE, _DATE_RE, _DOCTOR_RE, _MEDICAL_DECISION_RE):
        for match in pattern.finditer(text):
            if match.group(0).casefold() not in folded_sources:
                return True
    return False


class AnythingLLMEmployeeKnowledgeTool(BaseTool):
    """CrewAI tool the Knowledge Agent uses to read Employee Knowledge."""

    name: str = "anythingllm_employee_knowledge"
    description: str = (
        "Search the EstetikAI Employee Knowledge workspace in AnythingLLM. "
        "Use this before stating any company fact. "
        "The tool returns verified excerpts and a not_found list. "
        "Never replace a not_found item with outside knowledge."
    )
    args_schema: type[BaseModel] = AnythingLLMQueryInput

    def _run(self, question: str) -> str:
        try:
            lookup = AnythingLLMClient().query(question)
        except AnythingLLMIntegrationError as exc:
            settings = get_settings()
            lookup = KnowledgeLookup(
                mode="live",
                workspace=settings.anythingllm_employee_workspace_slug or "EstetikAI – Employee Knowledge",
                question=question.strip(),
                verified_information=[],
                not_found=restricted_topics_in(question),
                sources=[],
                integration_error=str(exc),
            )
        _remember(lookup)
        return json.dumps(lookup.model_dump(), ensure_ascii=False)


def query_public_assistant(question: str) -> KnowledgeLookup:
    """Ask the public clinic workspace without touching the employee retrieval."""
    settings = get_settings()
    return AnythingLLMClient()._query_live(question, settings.anythingllm_public_workspace_slug)
