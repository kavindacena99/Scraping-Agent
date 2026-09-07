"""Single construction point for LangChain-compatible chat models."""
from __future__ import annotations

from research.config import ProviderSettings, get_llm_settings
from research.exceptions import ProviderConfigurationError


def _required_key(config: ProviderSettings) -> str:
    key = config.api_keys.get(config.provider, "").strip()
    if not key:
        raise ProviderConfigurationError(f"Missing API key for selected LLM provider: {config.provider}.")
    return key


def get_llm(config: ProviderSettings | None = None):
    config = config or get_llm_settings()
    key = _required_key(config)
    if config.provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=config.model, api_key=key, temperature=0)
    if config.provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(model=config.model, google_api_key=key, temperature=0)
    if config.provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=config.model, anthropic_api_key=key, temperature=0)
    raise ProviderConfigurationError(f"Unsupported LLM provider: {config.provider}.")

