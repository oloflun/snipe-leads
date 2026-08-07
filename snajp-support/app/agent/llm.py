"""Central LLM-klient — stödjer OpenAI, DeepSeek och Gemini, alla via samma
AsyncOpenAI-klient (DeepSeek och Gemini exponerar OpenAI-kompatibla endpoints).

En enda plats som bygger klienten så triage, agent, vision och embeddings
delar konfiguration. Primärmodellen är DeepSeek; DeepSeek saknar embeddings
och dokumenterat bildstöd, så vision-sidovagnen (G9) och embeddings går mot
Gemini i stället — vald för gratisnivån (se scripts/keys.py, DEPLOY_KEYS.md).
"""

from functools import lru_cache

from openai import AsyncOpenAI

from ..config import Settings, get_settings

_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


def _resolve_base_url(settings: Settings) -> str | None:
    if settings.llm_base_url:
        return settings.llm_base_url
    if settings.llm_provider == "deepseek":
        return _DEEPSEEK_BASE_URL
    return None  # OpenAI SDK-default


def _looks_real(key: str) -> bool:
    return bool(key) and len(key) >= 20 and "..." not in key and "din-" not in key


@lru_cache
def get_llm_client() -> AsyncOpenAI:
    """Chat-klienten för aktuell provider (openai/deepseek)."""
    settings = get_settings()
    return AsyncOpenAI(api_key=settings.active_llm_key(), base_url=_resolve_base_url(settings))


@lru_cache
def get_embedding_client() -> AsyncOpenAI | None:
    """Embeddings går mot Gemini (gratisnivå). None => ingen vektor-embedding
    (full-text-fallback i KB-sökningen)."""
    settings = get_settings()
    key = settings.embedding_api_key or settings.gemini_api_key
    if not _looks_real(key):
        return None
    return AsyncOpenAI(api_key=key, base_url=_GEMINI_BASE_URL)


@lru_cache
def get_vision_client() -> AsyncOpenAI | None:
    """G9: vision-sidovagnen går mot Gemini (gratisnivå), oavsett llm_provider
    — deepseek-v4-flash saknar dokumenterat bildstöd. Samma nyckelupplösning
    som embeddings. None => ingen bildbeskrivning möjlig (se agent/vision.py
    för fallback-beteendet)."""
    settings = get_settings()
    key = settings.embedding_api_key or settings.gemini_api_key
    if not _looks_real(key):
        return None
    return AsyncOpenAI(api_key=key, base_url=_GEMINI_BASE_URL)


def get_agent_model():
    """Tvinga Agents SDK till Chat Completions (DeepSeek stödjer ej Responses API)."""
    from agents import OpenAIChatCompletionsModel

    settings = get_settings()
    return OpenAIChatCompletionsModel(model=settings.model, openai_client=get_llm_client())


def configure_agents_sdk() -> None:
    """Kör en gång i live-läge: stäng av tracing (annars nås OpenAI:s trace-backend
    med fel nyckel). Modell-routningen sköts av get_agent_model()."""
    from agents import set_tracing_disabled

    set_tracing_disabled(True)
