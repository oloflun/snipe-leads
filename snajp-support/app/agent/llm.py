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

import httpx
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


#: Förnya så här långt före utgången, i en bakgrundstråd. Googles token gäller
#: en timme och räknas som utgången 3 min 45 s i förväg (klockmarginalen i
#: google-auth), så tio minuter ger gott om tid för ett omtag.
_FORNYA_FORE_S = 600
#: Det längsta en förnyelse får blockera. google-auths standard är 120 s.
_FORNYELSE_TIMEOUT_S = 10
_fornyelse_pagar = threading.Event()


def _fornyelseanrop():
    """google-auths HTTP-anrop med vår tidsgräns i stället för 120 s."""
    from google.auth.transport.requests import Request

    anrop = Request()

    def med_tidsgrans(*args, **kwargs):
        kwargs["timeout"] = _FORNYELSE_TIMEOUT_S
        return anrop(*args, **kwargs)

    return med_tidsgrans


def _sekunder_kvar(creds) -> float | None:
    utgang = getattr(creds, "expiry", None)
    if utgang is None:
        return None
    from datetime import datetime, timezone

    nu = datetime.now(timezone.utc).replace(tzinfo=None)  # google-auth bär naiv UTC
    return (utgang - nu).total_seconds()


def _fornya_i_bakgrunden(creds) -> None:
    """Hämtar en ny token i en egen tråd, UTAN att hålla `_vertex_lock`.

    Låset får inte hållas över nätanropet: den som då frågar efter tokenen
    från händelseloopen väntar på låset, alltså på nätet, och det är just den
    frysningen som ska bort. `creds.refresh` byter token och utgång först när
    svaret kommit, så en läsare ser antingen den gamla (giltiga) eller den nya.
    """
    if _fornyelse_pagar.is_set():
        return
    _fornyelse_pagar.set()

    def kor() -> None:
        try:
            creds.refresh(_fornyelseanrop())
            logger.debug("Vertex AI-token förnyad i bakgrunden")
        except Exception as fel:  # noqa: BLE001 — nästa anrop försöker igen
            logger.warning("Vertex AI-tokenen kunde inte förnyas i förväg (%s).", type(fel).__name__)
        finally:
            _fornyelse_pagar.clear()

    threading.Thread(target=kor, name="vertex-token", daemon=True).start()


def _vertex_token(settings: Settings) -> str:
    """Aktuell OAuth2-token.

    Anropas synkront från händelseloopen (klienternas api_key sätts före varje
    anrop), så den får inte vänta på nätet i onödan. Före 2026-11-09 gjordes
    förnyelsen här, en gång i timmen, som ett blockerande HTTPS-anrop med 120 s
    tidsgräns — hela api:t stod still så länge (Fas 0-fyndet H7). Nu:

      * giltig token med mer än tio minuter kvar: returnera den;
      * giltig men nära utgången: returnera den och förnya i en bakgrundstråd;
      * saknas eller utgången (första anropet, eller en process som stått
        orörd i en timme): förnya här, men högst tio sekunder.

    `varm_vertex_token` tar det första fallet vid uppstart, utanför loopen.
    """
    creds = _vertex_credentials(settings.google_service_account_json)
    if creds.token and not creds.expired:
        kvar = _sekunder_kvar(creds)
        if kvar is not None and kvar < _FORNYA_FORE_S:
            _fornya_i_bakgrunden(creds)
        return creds.token
    with _vertex_lock:
        if not creds.token or creds.expired:
            creds.refresh(_fornyelseanrop())
            logger.debug("Vertex AI-token refreshad")
        return creds.token


async def varm_vertex_token(settings: Settings) -> None:
    """Hämtar den första tokenen i en tråd vid uppstart, och håller den färsk.

    Utan det blockerar det första kundanropet efter varje deploy på
    tokenhämtningen, och en process utan trafik i en timme gör om det. Slingan
    väcks var femte minut; `_vertex_token` startar själv bakgrundsförnyelsen
    när tokenen närmar sig utgången. Fel här får aldrig fälla uppstarten:
    nästa riktiga anrop försöker igen och rapporterar felet där det hör hemma.
    """
    import asyncio

    if not _uses_vertex(settings):
        return
    while True:
        try:
            await asyncio.to_thread(_vertex_token, settings)
        except Exception as fel:  # noqa: BLE001
            logger.warning("Vertex AI-tokenen kunde inte hämtas i förväg (%s).", type(fel).__name__)
        await asyncio.sleep(300)


def vertex_regioner(settings: Settings) -> list[str]:
    """Huvudregionen följd av reservregionerna (bara EU, se config)."""
    reserv = [r.strip() for r in (settings.vertex_reservregioner or "").split(",") if r.strip()]
    return list(dict.fromkeys([settings.google_cloud_region, *reserv]))


def _vertex_base_url(settings: Settings, region: str | None = None) -> str:
    """OpenAI-kompatibla Vertex AI-endpointen."""
    info = json.loads(settings.google_service_account_json)
    project = info["project_id"]
    region = region or settings.google_cloud_region
    return (
        f"https://{region}-aiplatform.googleapis.com/v1beta1/"
        f"projects/{project}/locations/{region}/endpoints/openapi/"
    )


def _uses_vertex(settings: Settings) -> bool:
    return settings.llm_provider == "gemini" and bool(settings.google_service_account_json)


# --- Modellnamnet mot Vertex ----------------------------------------------------
#
# Vertex OpenAI-kompatibla endpoint (`endpoints/openapi/`) kräver
# `<publisher>/<modell>`. Ett bart `gemini-2.5-flash` svarar
#
#     400 Malformed publisher model (`model`: 'gemini-2.5-flash') for the
#     'openapi' request endpoint ID; expected '<publisher>/<model>'.
#
# Uppmätt 2026-09-14 mot båda miljöernas service account: `google/gemini-2.5-
# flash` ger 200 (även i JSON-läge), bart namn ger 400 — i BÅDA miljöerna. Varje
# agentanrop har alltså fallit sedan flytten till Vertex (b1a651e), medan
# /health/ready svarade `mode: live`: hälsokontrollen mäter att credentials
# finns, inte att modellnamnet går igenom.
#
# Prefixet läggs HÄR, på klienten, och inte i `MODEL`:
#
#   * `discovery.py` anropar Vertex NATIVE-endpoint
#     (`publishers/google/models/{modell}:generateContent`), där modellen redan
#     står i sökvägen och ett prefix hade gett en dubbel publisher — bart namn
#     ger 200 där. Ett prefixat `MODEL` hade brutit leadssökningen.
#   * `provider_for_model()` känner igen `gemini…`, inte `google/gemini…`, så
#     uppstartskontrollen mot fel modellfamilj hade tyst slutat mäta.
#   * Anropsställena är många (run_step, triage, bokföring, retention,
#     strukturera, vision, Agents SDK). Ett prefix per anropsställe är åtta
#     ställen att glömma — klienten är det enda de alla passerar.


def vertex_modellnamn(namn: str) -> str:
    """Modellnamnet som Vertex openapi-endpoint vill ha: `google/<modell>`.

    Ett namn som redan bär en publisher (`google/…`, `meta/…`) lämnas orört —
    en uttryckligt satt publisher är ett beslut, inte ett fel att rätta.
    """
    rent = (namn or "").strip()
    if not rent or "/" in rent:
        return rent
    return f"google/{rent}"


def _med_vertex_modellnamn(client: AsyncOpenAI) -> AsyncOpenAI:
    """Låt klientens chat.completions.create prefixa modellnamnet.

    `client.chat` och `.completions` är cached_property i openai-SDK:n, så
    objektet är detsamma vid varje anrop — och Agents SDK går via exakt samma
    `create` (openai_chatcompletions.py: `self._get_client().chat.completions
    .create(**create_kwargs)`). Idempotent: en redan omsluten klient omsluts
    inte igen, annars hade en omläst cache gett `google/google/…`.
    """
    completions = client.chat.completions
    original = completions.create
    if getattr(original, "_vertex_modellnamn", False):
        return client

    async def create(*args, **kwargs):
        if "model" in kwargs:
            kwargs["model"] = vertex_modellnamn(kwargs["model"])
        return await original(*args, **kwargs)

    create._vertex_modellnamn = True  # type: ignore[attr-defined]
    completions.create = create  # type: ignore[method-assign]
    return client


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


# --- Geminis tänkande ---------------------------------------------------------

GEMINI_REASONING_EFFORT = ("none", "minimal", "low", "medium", "high")

#: Tänkandet AV. Uppmätt mot Vertex 2026-09-19 (gemini-2.5-flash):
#: `reasoning_effort="none"` ger 400 ("Expected one of: high, low, max,
#: medium, minimal"), och "minimal" stänger INTE av tänkandet (48 tänktokens
#: mot 51 utan parameter). Budget 0 via extra_body ger 0 tänktokens. Den
#: nästlade formen är AI Studios dokumenterade — och Vertex godtar den också.
TANKANDE_AV = {"extra_body": {"extra_body": {"google": {"thinking_config": {"thinking_budget": 0}}}}}


def gemini_tank_kwargs(mode: str | None, effort: str) -> dict:
    """Geminis tänkande. "none" = av (tankebudget 0), övriga värden skickas som
    OpenAI-kompatibilitetens `reasoning_effort`.

    Tomt `effort` = ingenting skickas (leverantörens default). Ett steg som
    uttryckligen vill tänka (thinking="enabled") får alltid leverantörens
    default — eskaleringsbedömningen ska inte strypas av en kostnadsflagga.
    Ett okänt värde skickas inte: ett felstavat env-värde ska inte ge 400 på
    varje agentanrop.
    """
    if not effort or mode == "enabled" or effort not in GEMINI_REASONING_EFFORT:
        return {}
    if effort == "none":
        return TANKANDE_AV
    return {"reasoning_effort": effort}


def tankande_kwargs() -> dict:
    """För småanropen UTANFÖR stegmotorn (klassificerare, sammanfattningar,
    bildbeskrivning): samma inställning som stegen, bara på Gemini.

    Uppmätt i development 2026-09-19: uppsägningsklassificeraren tänkte i
    snitt 408 tokens för att skriva 30 — tänkandet var nästan hela anropets
    kostnad."""
    settings = get_settings()
    if settings.llm_provider != "gemini":
        return {}
    return gemini_tank_kwargs(None, settings.gemini_reasoning_effort.strip().lower())


# --- Klienterna ---------------------------------------------------------------
#
# Vertex AI-tokens går ut efter ~1 timme. Klienterna cachelagras i module-
# globala variabler och deras api_key uppdateras före varje hämtning. Det
# fungerar eftersom openai SDK:n läser self.api_key i _build_headers() vid
# varje request, inte vid __init__.

def _tidsgrans(settings: Settings) -> httpx.Timeout:
    """Tidsgränsen för ETT LLM-anrop.

    Ingen klient hade en egen gräns före 2026-11-09 (Fas 0-fyndet K6): SDK:ns
    standard är 600 s, så ett anrop som Vertex slutat svara på höll en av
    chattens fyra arbetare i tio minuter — medan jobbet redan visats som
    misslyckat efter fem. Anslutningen får tio sekunder; hela svaret får
    LLM_TIMEOUT_S (standard 120 s, det längsta ett friskt researchanrop tar
    med marginal). Chatten har dessutom en egen, kortare gräns per steg i
    step_runner.
    """
    return httpx.Timeout(float(settings.llm_timeout_s), connect=10.0)


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


#: Vertex-klienter för reservregionerna (get_llm_client(region=...)).
_regionklienter: dict[str, AsyncOpenAI] = {}


def get_llm_client(region: str | None = None) -> AsyncOpenAI:
    """Chat-klienten för aktuell provider (openai/deepseek/gemini).

    Vertex AI: tokenen refreshas vid varje anrop. Klienten skapas en gång
    och api_key uppdateras — SDK:n läser den per request.

    `region` (Vertex): en klient mot en annan EU-region, för bakgrundsjobbens
    byte vid 429 (step_runner). Huvudregionen ger den vanliga klienten.
    """
    global _llm_client
    krav_tillaten_provider()
    settings = get_settings()

    if region and _uses_vertex(settings) and region != settings.google_cloud_region:
        with _clients_lock:
            klient = _regionklienter.get(region)
            if klient is None:
                klient = AsyncOpenAI(
                    api_key=_vertex_token(settings),
                    base_url=_vertex_base_url(settings, region),
                    max_retries=1,
                    timeout=_tidsgrans(settings),
                )
                _med_vertex_modellnamn(klient)
                _regionklienter[region] = klient
            else:
                klient.api_key = _vertex_token(settings)
            return klient

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
            timeout=_tidsgrans(settings),
        )
        if _uses_vertex(settings):
            _med_vertex_modellnamn(_llm_client)
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
                timeout=_tidsgrans(settings),
            )
            return _embedding_client

    key = settings.embedding_api_key or settings.gemini_api_key
    if not _looks_real(key):
        return None

    with _clients_lock:
        if _embedding_client is not None:
            return _embedding_client
        _embedding_client = AsyncOpenAI(
            api_key=key, base_url=_GEMINI_BASE_URL, timeout=_tidsgrans(settings)
        )
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
            _vision_client = _med_vertex_modellnamn(
                AsyncOpenAI(
                    api_key=_vertex_token(settings),
                    base_url=_vertex_base_url(settings),
                    timeout=_tidsgrans(settings),
                )
            )
            return _vision_client

    key = settings.embedding_api_key or settings.gemini_api_key
    if not _looks_real(key):
        return None

    with _clients_lock:
        if _vision_client is not None:
            return _vision_client
        _vision_client = AsyncOpenAI(
            api_key=key, base_url=_GEMINI_BASE_URL, timeout=_tidsgrans(settings)
        )
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
