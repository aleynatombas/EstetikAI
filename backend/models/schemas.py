"""Structured contracts passed between agents.

AnythingLLM is the only source of company facts. These models describe
how a fact is carried; they do not contain clinic prices, schedules, or staff.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# Topics the assistant must not invent. Detection is lexical so the safety
# check does not depend on the language model.
RESTRICTED_TOPICS: dict[str, tuple[str, ...]] = {
    "price": ("fiyat", "ücret", "ucret", "price", "cost", "kaç para", "kac para"),
    "appointment_date": ("randevu", "appointment", "müsait", "musait", "availability"),
    "medical_suitability": ("uygunluk", "uygun mu", "suitability", "eligible"),
    "doctor_name": ("doktor", "hekim", "doctor", "surgeon"),
    "staff_or_department_name": ("departman", "department", "çalışan adı", "calisan adi"),
    "package_contents": ("paket", "package"),
    "lodging_or_transfer": ("otel", "konaklama", "transfer", "hotel", "havalimanı", "havalimani"),
    "diagnosis_or_treatment_guarantee": (
        "teşhis",
        "teshis",
        "tedavi öner",
        "tedavi oner",
        "garanti",
        "guarantee",
    ),
}


class IntakeResult(BaseModel):
    request_type: str = Field(description="Kısa Türkçe etiket. Örnek: Ziyaretçi talebi.")
    category: str = Field(description="Kısa Türkçe etiket. Örnek: Saç ekimi.")
    priority: str = Field(description="Low, Medium veya High. Ekranda Türkçe gösterilir.")
    missing_information: list[str] = Field(default_factory=list)


class KnowledgeSnippet(BaseModel):
    source: str
    text: str


class KnowledgeSource(BaseModel):
    """One citation returned by AnythingLLM. Only fields the workspace sent are kept."""

    title: str = ""
    text: str = ""
    score: float | None = None


class KnowledgeLookup(BaseModel):
    """Return shape of the AnythingLLM tool, in mock mode and in live mode."""

    mode: Literal["mock", "live"]
    workspace: str
    question: str
    verified_information: list[KnowledgeSnippet] = Field(default_factory=list)
    not_found: list[str] = Field(default_factory=list)
    sources: list[KnowledgeSource] = Field(default_factory=list)
    integration_error: str | None = None


class KnowledgeResult(BaseModel):
    verified_information: list[str] = Field(default_factory=list)
    not_found: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)


class OperationsResult(BaseModel):
    recommended_actions: list[str] = Field(default_factory=list)
    human_confirmation_needed: list[str] = Field(default_factory=list)


class FinalResponse(BaseModel):
    request_type: str
    category: str
    priority: str
    verified_information: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    escalation_required: bool
    reason: str


def restricted_topics_in(text: str) -> list[str]:
    """Return restricted topic ids mentioned in ``text``, in stable order."""
    folded = text.casefold()
    found: list[str] = []
    for topic, needles in RESTRICTED_TOPICS.items():
        if any(needle.casefold() in folded for needle in needles):
            found.append(topic)
    return found
