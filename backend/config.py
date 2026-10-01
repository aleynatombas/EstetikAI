"""Environment-backed settings. Provider names are never hard-coded."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

# Local case-study default. A provider key in the environment still works.
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")


class ConfigError(RuntimeError):
    """Raised when required environment configuration is missing or invalid."""


def _clean(name: str) -> str:
    return os.getenv(name, "").strip()


def _as_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    llm_provider: str
    llm_model: str
    llm_api_key: str
    llm_base_url: str
    anythingllm_base_url: str
    anythingllm_api_key: str
    anythingllm_employee_workspace_slug: str
    anythingllm_public_workspace_slug: str
    mock_mode: bool

    def llm_model_name(self) -> str:
        """CrewAI/LiteLLM model id.

        ``LLM_PROVIDER=groq`` and ``LLM_MODEL=openai/gpt-oss-120b`` become
        ``groq/openai/gpt-oss-120b``. A model that already starts with the
        provider is left unchanged. If the provider is empty, ``LLM_MODEL``
        must already be ``provider/model``.
        """
        model = self.llm_model.strip()
        provider = self.llm_provider.strip()
        if provider and model:
            prefix = f"{provider}/"
            if model.casefold().startswith(prefix.casefold()):
                return model
            return f"{provider}/{model}"
        if "/" in model:
            return model
        raise ConfigError(
            "LLM_PROVIDER ve LLM_MODEL .env içinde tanımlı olmalı. "
            "LLM_MODEL zaten 'provider/model' biçimindeyse LLM_PROVIDER boş kalabilir."
        )

    def require_llm(self) -> None:
        self.llm_model_name()
        if not self.llm_api_key:
            raise ConfigError("LLM_API_KEY .env içinde tanımlı olmalı.")

    def missing_anythingllm(self) -> list[str]:
        missing: list[str] = []
        if not self.anythingllm_base_url:
            missing.append("ANYTHINGLLM_BASE_URL")
        if not self.anythingllm_api_key:
            missing.append("ANYTHINGLLM_API_KEY")
        if not self.anythingllm_employee_workspace_slug:
            missing.append("ANYTHINGLLM_EMPLOYEE_WORKSPACE_SLUG")
        return missing


def get_settings() -> Settings:
    return Settings(
        llm_provider=_clean("LLM_PROVIDER"),
        llm_model=_clean("LLM_MODEL"),
        llm_api_key=_clean("LLM_API_KEY"),
        llm_base_url=_clean("LLM_BASE_URL"),
        anythingllm_base_url=_clean("ANYTHINGLLM_BASE_URL").rstrip("/"),
        anythingllm_api_key=_clean("ANYTHINGLLM_API_KEY"),
        anythingllm_employee_workspace_slug=_clean("ANYTHINGLLM_EMPLOYEE_WORKSPACE_SLUG"),
        anythingllm_public_workspace_slug=_clean("ANYTHINGLLM_PUBLIC_WORKSPACE_SLUG")
        or "estetikai-public-knowledge",
        mock_mode=_as_bool("MOCK_MODE", default=True),
    )
