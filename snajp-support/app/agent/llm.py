"""Central LLM-klient — stödjer OpenAI, DeepSeek och Gemini, alla via samma
AsyncOpenAI-klient (DeepSeek och Gemini exponerar OpenAI-kompatibla endpoints).

En enda plats som bygger klienten så triage, agent, vision och embeddings
delar konfiguration. DeepSeek saknar embeddings och dokumenterat bildstöd, så
vision-sidovagnen (G9) och embeddings går mot Gemini i stället — vald för
gratisnivån (se scripts/keys.py, DEPLOY_KEYS.md).

## DeepSeek är INTE längre primärmodell (beslut 2026-08-24)

DeepSeek behandlar prompten i Kina. Allt som går genom support-agenten är
kundens kundmejl, alltså personuppgifter som kunden är ansvarig för och vi är
biträde för. En sådan tredjelandsöverföring kräver SCC, en
överföringskonsekvensbedömning och ett uttryckligt villkor i PUB-avtalet —
inget av det finns.

DeepSeek får därför köras bara mot syntetisk data: lokalt och i testsviten,
mot MemoryStorage och fixtures. `Settings.llm_provider_fault()` avgör var
gränsen går, och `get_llm_client()` nedan vägrar bygga en klient som bryter
mot den. Se även startkontrollen i app/main.py — den fäller BYGGET, inte det
första anropet, så en felaktig deploy dör högljutt i stället för att tyst
skicka kunddata utomlands.
"""

from functools import lru_cache

from openai import AsyncOpenAI

from ..config import Settings, get_settings

_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


def _resolve_base_url(settings: Settings) -> str | None:
    """Endpointen för den valda providern. None => OpenAI SDK-default.

    Gemini står med sedan 2026-08-24: den drev redan vision och embeddings mot
    samma OpenAI-kompatibla endpoint, men var aldrig kopplad som CHATT-provider.
    LLM_PROVIDER=gemini pekade därför mot OpenAI:s endpoint med tom nyckel —
    se `Settings.active_llm_key` för hela historien.
    """
    if settings.llm_base_url:
        return settings.llm_base_url
    if settings.llm_provider == "deepseek":
        return _DEEPSEEK_BASE_URL
    if settings.llm_provider == "gemini":
        return _GEMINI_BASE_URL
    return None  # OpenAI SDK-default


def _looks_real(key: str) -> bool:
    return bool(key) and len(key) >= 20 and "..." not in key and "din-" not in key


class ForbjudenProviderIMiljon(RuntimeError):
    """Providern får inte användas i den här miljön. Se Settings.llm_provider_fault."""


def krav_tillaten_provider() -> None:
    """Kastar om den konfigurerade providern är förbjuden här.

    Anropas på två ställen: vid uppstart (app/main.py) och vid varje
    klientbygge nedan. Uppstartskontrollen är den som ska smälla; den här är
    bältet till hängslet, för den dag någon bygger en ny ingång som inte går
    via lifespan (ett skript, ett cron-jobb, en test-harness mot skarp DB).
    """
    fel = get_settings().llm_provider_fault()
    if fel:
        raise ForbjudenProviderIMiljon(fel)


@lru_cache
def get_llm_client() -> AsyncOpenAI:
    """Chat-klienten för aktuell provider (openai/deepseek).

    OBS: `lru_cache` gör att kontrollen körs en gång per process. Det räcker —
    varken miljönamnet eller LLM_PROVIDER ändras under en processlivstid.
    """
    krav_tillaten_provider()
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
