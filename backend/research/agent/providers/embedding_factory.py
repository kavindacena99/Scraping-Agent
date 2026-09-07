"""Single construction point for LangChain-compatible embedding models."""
from __future__ import annotations

from research.config import ProviderSettings, get_embedding_settings
from research.exceptions import ProviderConfigurationError


def get_embedding_model(config: ProviderSettings | None = None):
    config = config or get_embedding_settings()
    key = config.api_keys.get(config.provider, "").strip()
    if not key:
        raise ProviderConfigurationError(f"Missing API key for selected embedding provider: {config.provider}.")
    if config.provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(model=config.model, api_key=key)
    if config.provider == "gemini":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        return GoogleGenerativeAIEmbeddings(model=config.model, google_api_key=key)
    raise ProviderConfigurationError(f"Unsupported embedding provider: {config.provider}.")

