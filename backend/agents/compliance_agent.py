"""Final review of the pipeline, plus a deterministic safety pass."""

from __future__ import annotations

import re

from crewai import Agent, LLM

from backend.agents import SAFETY_RULES
from backend.models.schemas import FinalResponse, KnowledgeLookup, restricted_topics_in

_PRICE_RE = re.compile(
    r"(?:€|\$|₺)\s*\d[\d.,]*|\b\d[\d.,]*\s*(?:€|eur|euro|usd|tl|₺|\$|dolar)\b",
    re.IGNORECASE,
)
_DOCTOR_RE = re.compile(r"\b(?:Dr\.?|Doktor|Doctor)\s+[A-ZÇĞİÖŞÜ][\wçğıöşüÇĞİÖŞÜ'-]+")
_DATE_RE = re.compile(r"\b\d{1,2}[./]\d{1,2}[./]\d{2,4}\b")
_MEDICAL_DECISION_RE = re.compile(
    r"tıbbi olarak uygun|operasyona uygun|uygun bir aday|uygun değildir|uygun degildir|"
    r"eligible for|not eligible|teşhis konul|teshis konul|tedavi öner|tedavi oner|"
    r"sonuç garanti|sonuc garanti|sonuç garant",
    re.IGNORECASE,
)
_COMPLETED_ACTION_RE = re.compile(
    r"randevu (?:oluşturuldu|olusturuldu|alındı|alindi|onaylandı|onaylandi|verildi)|"
    r"rezerve edildi|ödeme alındı|odeme alindi|işlem tamamlandı|islem tamamlandi|"
    r"already booked|appointment confirmed",
    re.IGNORECASE,
)


def create_compliance_agent(llm: LLM) -> Agent:
    return Agent(
        role="Compliance Agent",
        goal=(
            "Check the draft answer for invented or unauthorized information "
            "and return the final structured employee response."
        ),
        backstory=(
            "You are the last control before an EstetikAI employee sees the result. "
            "You keep request type, category, and priority from intake. "
            "You keep verified information only when it comes from the knowledge tool. "
            "You set escalation_required to true when a price, appointment, person, "
            "department, package, lodging, transfer, or medical decision is unsupported.\n"
            f"{SAFETY_RULES}"
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=3,
    )


def enforce_compliance(
    employee_request: str,
    draft: FinalResponse,
    retrieval: KnowledgeLookup | None,
) -> FinalResponse:
    """Replace model-written facts with the tool payload and force escalation when needed.

    The compliance agent still produces the draft. This pass is the trust boundary:
    verified lines are the AnythingLLM excerpts, not a paraphrase the model added.
    """
    data = draft.model_dump()
    reasons = [data["reason"].strip()] if data.get("reason", "").strip() else []
    data["priority"] = _normalize_priority(data.get("priority", ""))
    data["request_type"] = (data.get("request_type") or "Unknown").strip() or "Unknown"
    data["category"] = (data.get("category") or "Unspecified").strip() or "Unspecified"

    source_blob = ""
    must_escalate = False
    if retrieval is None:
        data["verified_information"] = []
        must_escalate = True
        reasons.append(
            "Kurumsal bilgi araması yapılmadığı için hiçbir bilgi doğrulanmış sayılmadı."
        )
    else:
        if retrieval.integration_error:
            data["verified_information"] = []
            must_escalate = True
            reasons.append(retrieval.integration_error)
        else:
            data["verified_information"] = [
                f"{snippet.source}: {snippet.text}" for snippet in retrieval.verified_information
            ]
        source_blob = "\n".join(data["verified_information"]).casefold()
        if retrieval.mode == "mock":
            reasons.append(
                "Canlı bağlantı kapalı; doğrulanan notlar deneme içeriğidir."
            )

    cleaned_actions: list[str] = []
    for action in data.get("recommended_actions") or []:
        text = str(action).strip()
        if not text:
            continue
        if _unsupported_specifics(text, source_blob) or _COMPLETED_ACTION_RE.search(text):
            must_escalate = True
            reasons.append(
                "Önerilen adım, doğrulanmamış somut bir iddia veya gerçekleşmemiş bir işlem içerdiği için kaldırıldı."
            )
            continue
        cleaned_actions.append(text)

    asked = set(restricted_topics_in(employee_request))
    if retrieval is None:
        unresolved = asked
    else:
        unresolved = asked.intersection(retrieval.not_found)
    if unresolved:
        must_escalate = True
        labels = {
            "price": "fiyat",
            "appointment_date": "randevu tarihi",
            "medical_suitability": "tıbbi uygunluk",
            "doctor_name": "hekim adı",
            "staff_or_department_name": "çalışan veya departman adı",
            "package_contents": "paket içeriği",
            "lodging_or_transfer": "konaklama veya transfer",
            "diagnosis_or_treatment_guarantee": "teşhis, tedavi veya sonuç garantisi",
        }
        readable = [labels.get(topic, topic) for topic in sorted(unresolved)]
        reasons.append(
            "Yalnızca belgede olmayan kısım insan onayına gider: " + ", ".join(readable) + "."
        )
        if not any(_routes_to_human(action) for action in cleaned_actions):
            cleaned_actions.append(
                "Fiyat, randevu veya tıbbi karar üretmeyin. Yalnızca bu kısmı insan onayına bırakın."
            )

    if not cleaned_actions:
        cleaned_actions.append(
            "Talebi insan onayına bırakın ve belgede olmayan ayrıntı eklemeyin."
            if must_escalate
            else "Talebi kayda geçirin. Ziyaretçi net bir soru sorarsa yeniden sınıflandırın."
        )
    if not must_escalate:
        reasons = [
            "Bu talep fiyat, randevu veya tıbbi karar istemiyor. Çalışan kaydı ilerletebilir."
        ]

    data["recommended_actions"] = _unique(cleaned_actions)
    data["missing_information"] = _unique(
        str(item).strip() for item in (data.get("missing_information") or []) if str(item).strip()
    )
    data["verified_information"] = _unique(data.get("verified_information") or [])
    data["escalation_required"] = must_escalate
    data["reason"] = " ".join(_unique(item for item in reasons if not _mostly_english(item)))
    return FinalResponse.model_validate(data)


def _normalize_priority(value: str) -> str:
    folded = value.strip().casefold()
    mapping = {
        "low": "Low",
        "düşük": "Low",
        "dusuk": "Low",
        "medium": "Medium",
        "orta": "Medium",
        "high": "High",
        "yüksek": "High",
        "yuksek": "High",
        "urgent": "High",
        "acil": "High",
    }
    return mapping.get(folded, "Medium")


def _unsupported_specifics(text: str, source_blob: str) -> list[str]:
    findings: list[str] = []
    for pattern in (_PRICE_RE, _DOCTOR_RE, _DATE_RE, _MEDICAL_DECISION_RE):
        for match in pattern.finditer(text):
            snippet = match.group(0)
            if snippet.casefold() not in source_blob:
                findings.append(snippet)
    return findings


def _mostly_english(text: str) -> bool:
    folded = f" {text.casefold()} "
    hints = (" the ", " greeting", " escalate", " classify", " record ", " request", " contact ")
    return sum(1 for hint in hints if hint in folded) >= 2


def _routes_to_human(action: str) -> bool:
    folded = action.casefold()
    markers = ("insan", "escalat", "eskalasyon", "onay", "human")
    return any(marker in folded for marker in markers)


def _unique(items) -> list[str]:
    seen: dict[str, None] = {}
    for item in items:
        text = str(item).strip()
        if text and text not in seen:
            seen[text] = None
    return list(seen)
