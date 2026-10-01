"""Assembles and runs the employee-request crew."""

from __future__ import annotations

import json
import os
import re

from backend.config import ConfigError, get_settings

from crewai import Crew, LLM, Process

from backend.agents.compliance_agent import create_compliance_agent, enforce_compliance
from backend.agents.intake_agent import create_intake_agent
from backend.agents.knowledge_agent import create_knowledge_agent
from backend.agents.operations_agent import create_operations_agent
from backend.models.schemas import FinalResponse
from backend.tasks.estetik_tasks import create_tasks
from backend.tools.anythingllm_tool import (
    AnythingLLMEmployeeKnowledgeTool,
    AnythingLLMIntegrationError,
    get_last_retrieval,
    reset_last_retrieval,
)


def build_llm() -> LLM:
    settings = get_settings()
    settings.require_llm()
    model_name = settings.llm_model_name()
    _export_provider_api_key(model_name, settings.llm_api_key)
    kwargs: dict[str, object] = {
        "model": model_name,
        "api_key": settings.llm_api_key,
        "temperature": 0.1,
    }
    if settings.llm_base_url:
        kwargs["base_url"] = settings.llm_base_url
    llm = LLM(**kwargs)
    if model_name.casefold().startswith("groq/"):
        _strip_unsupported_groq_fields(llm)
        _recover_groq_structured_tool_calls(llm)
    return llm


def _strip_unsupported_groq_fields(llm: LLM) -> None:
    """Groq rejects CrewAI's prompt-cache marker on chat messages."""
    original = llm._format_messages_for_provider

    def _format(messages: list) -> list:
        formatted = original(messages)
        for message in formatted:
            if isinstance(message, dict):
                message.pop("cache_breakpoint", None)
        return formatted

    llm._format_messages_for_provider = _format  # type: ignore[method-assign]


def _recover_groq_structured_tool_calls(llm: LLM) -> None:
    """Turn Groq's rejected structured-output tool call into plain JSON text.

    gpt-oss sometimes answers with a tool name that was not declared. Groq
    rejects that generation. The arguments are still the task JSON.
    """
    original_call = llm.call

    def _call(*args, **kwargs):
        try:
            return original_call(*args, **kwargs)
        except Exception as exc:
            recovered = _structured_json_from_groq_error(exc)
            if recovered is None:
                raise
            return recovered

    llm.call = _call  # type: ignore[method-assign]


def _structured_json_from_groq_error(exc: Exception) -> str | None:
    text = str(exc)
    if "tool_use_failed" not in text or "was not in request.tools" not in text:
        return None
    match = re.search(r'"failed_generation"\s*:\s*"((?:\\.|[^"\\])*)"', text)
    if match is None:
        return None
    try:
        decoded = json.loads(f'"{match.group(1)}"')
        payload = json.loads(decoded)
    except json.JSONDecodeError:
        return None
    arguments = payload.get("arguments") if isinstance(payload, dict) else None
    if isinstance(arguments, str):
        return arguments
    if isinstance(arguments, dict):
        return json.dumps(arguments, ensure_ascii=False)
    return None


def _export_provider_api_key(model_name: str, api_key: str) -> None:
    """Expose LLM_API_KEY under the provider variable LiteLLM usually reads."""
    provider = model_name.split("/", 1)[0].strip().upper()
    if not provider:
        return
    os.environ.setdefault(f"{provider}_API_KEY", api_key)
    if provider == "GOOGLE":
        os.environ.setdefault("GEMINI_API_KEY", api_key)
    elif provider == "GEMINI":
        os.environ.setdefault("GOOGLE_API_KEY", api_key)


def run_employee_request(employee_request: str) -> dict:
    """Run Intake → Knowledge → Operations → Compliance and return the final JSON object."""
    cleaned = employee_request.strip()
    if not cleaned:
        raise ConfigError("Çalışan talebi boş olamaz.")

    reset_last_retrieval()
    llm = build_llm()
    knowledge_tool = AnythingLLMEmployeeKnowledgeTool()
    intake_agent = create_intake_agent(llm)
    knowledge_agent = create_knowledge_agent(llm, knowledge_tool)
    operations_agent = create_operations_agent(llm)
    compliance_agent = create_compliance_agent(llm)
    tasks = create_tasks(
        intake_agent,
        knowledge_agent,
        operations_agent,
        compliance_agent,
        knowledge_tool,
    )
    crew = Crew(
        agents=[intake_agent, knowledge_agent, operations_agent, compliance_agent],
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
    )
    try:
        result = crew.kickoff(inputs={"employee_request": cleaned})
    except AnythingLLMIntegrationError as exc:
        return _integration_escalation(exc)
    draft = _final_from_crew(result)
    final = enforce_compliance(cleaned, draft, get_last_retrieval())
    return final.model_dump()


def _integration_escalation(exc: AnythingLLMIntegrationError) -> dict:
    """Live AnythingLLM failed. Do not replace the failure with mock documents."""
    final = FinalResponse(
        request_type="Unknown",
        category="Unspecified",
        priority="High",
        verified_information=[],
        missing_information=[],
        recommended_actions=[
            "AnythingLLM Employee Knowledge yanıt vermedi. Talebi insan onayına bırakın ve kurumsal bilgi eklemeyin."
        ],
        escalation_required=True,
        reason=str(exc),
    )
    return final.model_dump()


def _final_from_crew(result: object) -> FinalResponse:
    pydantic_output = getattr(result, "pydantic", None)
    if isinstance(pydantic_output, FinalResponse):
        return pydantic_output
    if pydantic_output is not None:
        return FinalResponse.model_validate(pydantic_output)

    json_dict = getattr(result, "json_dict", None)
    if isinstance(json_dict, dict):
        return FinalResponse.model_validate(json_dict)

    raw = getattr(result, "raw", result)
    return _final_from_text(str(raw))


def _final_from_text(raw: str) -> FinalResponse:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        raise ConfigError("Crew çıktısı yapılandırılmış final JSON içermiyor.")
    try:
        payload = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise ConfigError("Crew final çıktısı JSON olarak okunamadı.") from exc
    return FinalResponse.model_validate(payload)
