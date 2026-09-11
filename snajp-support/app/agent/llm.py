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

## Vertex AI (2026-09)

Google AI Studio tog bort möjligheten att använda Cloud-krediter. Gemini-
anropen kräver nu Vertex AI med service account JSON + OAuth2-tokens.
Endpointen är OpenAI-kompatibel men URL och auth skiljer sig:

  AI Studio:  generativelanguage.googleapis.com  + ?key=API_KEY
  Vertex AI:  {region}-aiplatform.googleapis.com  + Bearer <oauth2-token>

Tokens går ut efter ~1 timme. `_vertex_credentials()` cachar credentials-
objektet, och `_vertex_token()` refreshar tokenen vid behov. Klienterna
(chat, embeddings, vision) skapas en gång men uppdaterar sin `api_key`
före varje hämtning via `_refresh_vertex_clients()`.
"""

from __future__ import annotations

import json
import logging
import threading
from functools import lru_cache

from openai import AsyncOpenAI

from ..config import Settings, get_settings

logger = logging.getLogger(__name__)

_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
_VERTEX_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]

# --- Vertex AI token-hantering ------------------------------------------------

_vertex_lock = threading.Lock()
_vertex_creds = None  # google.oauth2.service_account.Credentials | None


def _vertex_credentials(sa_json: str):
    """Bygger (eller returnerar cachade) Vertex AI-credentials ur JSON-strängen."""
    global _vertex_creds
    with _vertex_lock:
        if _vertex_creds is not None:
            return _vertex_creds
        from google.oauth2 import service_account
        info = json.loads(sa_json)
        _vertex_creds = service_account.Credentials.from_service_account_info(
            info, scopes=_VERTEX_SCOPES,
        )
        return _vertex_creds


def _vertex_token(settings: Settings) -> str:
    """Aktuell OAuth2-token, refreshad om den gått ut."""
    from google.auth.transport.requests import Request
    creds = _vertex_credentials(settings.google_service_account_json)
    with _vertex_lock:
        if not creds.token or creds.expired:
            creds.refresh(Request())
            logger.debug("Vertex AI-token refreshad")
        return creds.token


def _vertex_base_url(settings: Settings) -> str:
    """OpenAI-kompatibla Vertex AI-endpointen."""
    info = json.loads(settings.google_service_account_json)
    project = info["project_id"]
    region = settings.google_cloud_region
    return (
        f"https://{region}-aiplatform.googleapis.com/v1beta1/"
        f"projects/{project}/locations/{region}/endpoints/openapi/"
    )


def _uses_vertex(settings: Settings) -> bool:
    return settings.llm_provider == "gemini" and bool(settings.google_service_account_json)


# --- URL-upplösning -----------------------------------------------------------


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
        if settings.google_service_account_json:
            return _vertex_base_url(settings)
        return _GEMINI_BASE_URL
    return None  # OpenAI SDK-default


def _gemini_key_and_url(settings: Settings) -> tuple[str, str]:
    """Nyckel + bas-URL för Gemini-sidovagnarna (embeddings, vision).

    Vertex AI om service account finns, annars AI Studio med gemini_api_key.
    """
    if settings.google_service_account_json:
        return _vertex_token(settings), _vertex_base_url(settings)
    key = settings.embedding_api_key or settings.gemini_api_key
    return key, _GEMINI_BASE_URL


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


# --- Klienterna ---------------------------------------------------------------
#
# Vertex AI-tokens går ut efter ~1 timme. Klienterna cachelagras i module-
# globala variabler och deras api_key uppdateras före varje hämtning. Det
# fungerar eftersom openai SDK:n läser self.api_key i _build_headers() vid
# varje request, inte vid __init__.

_llm_client: AsyncOpenAI | None = None
_embedding_client: AsyncOpenAI | None = None
_vision_client: AsyncOpenAI | None = None
_clients_lock = threading.Lock()


def _refresh_vertex_clients() -> None:
    """Uppdatera api_key på alla cachade klienter med aktuell Vertex-token."""
    settings = get_settings()
    if not _uses_vertex(settings):
        return
    token = _vertex_token(settings)
    with _clients_lock:
        for client in (_llm_client, _embedding_client, _vision_client):
            if client is not None:
                client.api_key = token


def get_llm_client() -> AsyncOpenAI:
    """Chat-klienten för aktuell provider (openai/deepseek/gemini).

    Vertex AI: tokenen refreshas vid varje anrop. Klienten skapas en gång
    och api_key uppdateras — SDK:n läser den per request.
    """
    global _llm_client
    krav_tillaten_provider()
    settings = get_settings()

    with _clients_lock:
        if _llm_client is not None:
            if _uses_vertex(settings):
                _llm_client.api_key = _vertex_token(settings)
            return _llm_client

        if _uses_vertex(settings):
            api_key = _vertex_token(settings)
        else:
            api_key = settings.active_llm_key()

        # max_retries=1 EXPLICIT — ett omtag, inte tre. Talet står utskrivet så
        # att beteendet är ett beslut och inte en följd av en
        # biblioteksuppgradering (SDK:ns egen default är 2).
        _llm_client = AsyncOpenAI(
            api_key=api_key,
            base_url=_resolve_base_url(settings),
            max_retries=1,
        )
        return _llm_client


def get_embedding_client() -> AsyncOpenAI | None:
    """Embeddings går mot Gemini. None => ingen vektor-embedding
    (full-text-fallback i KB-sökningen)."""
    global _embedding_client
    settings = get_settings()

    if settings.google_service_account_json:
        with _clients_lock:
            if _embedding_client is not None:
                _embedding_client.api_key = _vertex_token(settings)
                return _embedding_client
            _embedding_client = AsyncOpenAI(
                api_key=_vertex_token(settings),
                base_url=_vertex_base_url(settings),
            )
            return _embedding_client

    key = settings.embedding_api_key or settings.gemini_api_key
    if not _looks_real(key):
        return None

    with _clients_lock:
        if _embedding_client is not None:
            return _embedding_client
        _embedding_client = AsyncOpenAI(api_key=key, base_url=_GEMINI_BASE_URL)
        return _embedding_client


def get_vision_client() -> AsyncOpenAI | None:
    """G9: vision-sidovagnen går mot Gemini, oavsett llm_provider
    — deepseek-v4-flash saknar dokumenterat bildstöd. Samma nyckelupplösning
    som embeddings. None => ingen bildbeskrivning möjlig (se agent/vision.py
    för fallback-beteendet)."""
    global _vision_client
    settings = get_settings()

    if settings.google_service_account_json:
        with _clients_lock:
            if _vision_client is not None:
                _vision_client.api_key = _vertex_token(settings)
                return _vision_client
            _vision_client = AsyncOpenAI(
                api_key=_vertex_token(settings),
                base_url=_vertex_base_url(settings),
            )
            return _vision_client

    key = settings.embedding_api_key or settings.gemini_api_key
    if not _looks_real(key):
        return None

    with _clients_lock:
        if _vision_client is not None:
            return _vision_client
        _vision_client = AsyncOpenAI(api_key=key, base_url=_GEMINI_BASE_URL)
        return _vision_client


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
