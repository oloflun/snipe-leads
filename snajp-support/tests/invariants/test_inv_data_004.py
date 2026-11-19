"""INV-DATA-004: Google AI Studio bär aldrig kunddata.

Produktionen kör Gemini via Vertex AI i EU (servicekontot,
GOOGLE_SERVICE_ACCOUNT_JSON). Koden har kvar en reservväg till AI Studio
(generativelanguage.googleapis.com, GEMINI_API_KEY) för chatt, bildbeskrivning,
embeddings och den grundade sökningen. AI Studio ger ingen EU-bunden
behandling, och på gratisnivån får Google använda innehållet för att förbättra
sina produkter. GEMINI_API_KEY är satt i main och development, så ett
servicekonto som saknas eller inte går att läsa hade tyst skickat kundmejl dit.

Samma gräns som DeepSeek-spärren (`Settings.har_riktig_kunddata`): känt
kunddatamiljönamn eller en databas som inte ligger på loopback. Lokalt och i
testsviten fungerar AI Studio som förut.
"""

from __future__ import annotations

import json
from urllib.parse import urlsplit

import pytest

from app.agent import llm
from app.config import Settings, get_settings

_SA_JSON = json.dumps(
    {
        "type": "service_account",
        "project_id": "test-proj",
        "private_key_id": "abc",
        "private_key": "-----BEGIN RSA PRIVATE KEY-----\nfake\n-----END RSA PRIVATE KEY-----\n",
        "client_email": "sa@test-proj.iam.gserviceaccount.com",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
)
_NYCKEL = "test-key-not-a-real-credential-000000"
_FJARR_DB = "postgresql://u:p@db.exempel.se:5432/railway"


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _settings(**kwargs) -> Settings:
    return Settings(_env_file=None, **kwargs)


@pytest.fixture
def miljo(monkeypatch):
    """Sätter env, nollställer settings-cachen och de cachade klienterna."""

    def nollstall():
        for namn in ("_llm_client", "_vision_client", "_embedding_client"):
            monkeypatch.setattr(llm, namn, None)
        get_settings.cache_clear()

    def satt(**env):
        for namn, varde in env.items():
            monkeypatch.setenv(namn, varde)
        nollstall()

    monkeypatch.setattr(llm, "_vertex_token", lambda _s: "fejktoken")
    yield satt
    nollstall()


# -- (a) Riktig data + gemini + inget servicekonto -> uppstarten fälls -----------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"environment": "main"},
        {"environment": "development"},
        {"railway_environment_name": "development"},
        {"database_url": _FJARR_DB},
    ],
)
def test_gemini_utan_servicekonto_falls_dar_data_ar_riktig(kwargs):
    fel = _settings(llm_provider="gemini", gemini_api_key=_NYCKEL, **kwargs).llm_provider_fault()
    assert fel is not None
    assert "GOOGLE_SERVICE_ACCOUNT_JSON" in fel
    assert "AI Studio" in fel


@pytest.mark.parametrize(
    "trasig",
    ["{inte json", "[]", '{"project_id": "p"}', json.dumps({**json.loads(_SA_JSON), "private_key": ""})],
)
def test_olasbart_servicekonto_falls_dar_data_ar_riktig(trasig):
    fel = _settings(
        llm_provider="gemini", environment="main", gemini_api_key=_NYCKEL, google_service_account_json=trasig
    ).llm_provider_fault()
    assert fel is not None
    assert "går inte att läsa" in fel


@pytest.mark.anyio
async def test_lifespan_dor_innan_databasen_oppnas(miljo):
    from app.main import app, lifespan

    miljo(LLM_PROVIDER="gemini", MODEL="gemini-2.5-flash", ENVIRONMENT="main", GEMINI_API_KEY=_NYCKEL)
    with pytest.raises(RuntimeError, match="GOOGLE_SERVICE_ACCOUNT_JSON"):
        async with lifespan(app):
            pass


# -- (b) Riktig data + servicekonto -> ingen fällning, anropen går mot Vertex ---


def test_servicekonto_i_riktig_miljo_falls_inte():
    s = _settings(
        llm_provider="gemini", environment="main", gemini_api_key=_NYCKEL, google_service_account_json=_SA_JSON
    )
    assert s.llm_provider_fault() is None


def test_med_servicekonto_gar_alla_klienter_mot_vertex(miljo):
    miljo(
        LLM_PROVIDER="gemini",
        MODEL="gemini-2.5-flash",
        ENVIRONMENT="main",
        GEMINI_API_KEY=_NYCKEL,
        GOOGLE_SERVICE_ACCOUNT_JSON=_SA_JSON,
    )
    for klient in (llm.get_llm_client(), llm.get_vision_client(), llm.get_embedding_client()):
        # Värdnamnet jämförs exakt: en delsträngskontroll godkänner också en
        # adress som bara bär namnet någonstans i sökvägen.
        assert urlsplit(str(klient.base_url)).hostname == "europe-west1-aiplatform.googleapis.com"


# -- (c) Lokal data -> AI Studio tillåtet som förut -----------------------------


@pytest.mark.parametrize("kwargs", [{}, {"environment": "lokal"}, {"database_url": "postgresql://u:p@127.0.0.1:5432/x"}])
def test_lokalt_far_ai_studio_anvandas(kwargs):
    s = _settings(llm_provider="gemini", gemini_api_key=_NYCKEL, **kwargs)
    assert s.llm_provider_fault() is None
    assert llm._resolve_base_url(s) == llm._GEMINI_BASE_URL


def test_lokalt_bygger_sidovagnarna_mot_ai_studio(miljo):
    miljo(LLM_PROVIDER="gemini", MODEL="gemini-2.5-flash", ENVIRONMENT="lokal", GEMINI_API_KEY=_NYCKEL)
    assert str(llm.get_llm_client().base_url) == llm._GEMINI_BASE_URL
    assert str(llm.get_vision_client().base_url) == llm._GEMINI_BASE_URL
    assert str(llm.get_embedding_client().base_url) == llm._GEMINI_BASE_URL


# -- (d) Reservvägen vägrar när data är riktig, även med nyckeln satt ----------


def test_chattklienten_vagrar_ai_studio(miljo):
    miljo(LLM_PROVIDER="gemini", MODEL="gemini-2.5-flash", ENVIRONMENT="main", GEMINI_API_KEY=_NYCKEL)
    with pytest.raises(llm.ForbjudenProviderIMiljon):
        llm.get_llm_client()


def test_sidovagnarna_vagrar_ai_studio(miljo):
    """Sidovagnarna läser servicekontot oavsett LLM_PROVIDER, och en ingång
    utanför lifespan passerar aldrig uppstarten (som sedan INV-DATA-006 också
    vägrar openai), så spärren måste sitta i reservvägen."""
    miljo(LLM_PROVIDER="openai", MODEL="gpt-4o-mini", OPENAI_API_KEY=_NYCKEL, ENVIRONMENT="main", GEMINI_API_KEY=_NYCKEL)
    assert llm.get_vision_client() is None
    assert llm.get_embedding_client() is None
    with pytest.raises(llm.ForbjudenProviderIMiljon):
        llm._gemini_key_and_url(get_settings())


@pytest.mark.anyio
async def test_bildbeskrivningen_ber_om_eskalering_i_stallet(miljo):
    from app.agent.vision import describe_image

    miljo(LLM_PROVIDER="openai", MODEL="gpt-4o-mini", OPENAI_API_KEY=_NYCKEL, ENVIRONMENT="main", GEMINI_API_KEY=_NYCKEL)
    text = await describe_image("data:image/png;base64,AAAA")
    assert "Eskalera" in text


@pytest.mark.anyio
async def test_grundade_sokningen_vagrar_ai_studio(miljo, monkeypatch):
    from app.leads import discovery

    def inget_natanrop(*args, **kwargs):
        raise AssertionError("AI Studio anropades med riktig kunddata")

    monkeypatch.setattr(discovery.httpx, "AsyncClient", inget_natanrop)
    miljo(LLM_PROVIDER="gemini", MODEL="gemini-2.5-flash", DATABASE_URL=_FJARR_DB, GEMINI_API_KEY=_NYCKEL)
    with pytest.raises(discovery.DiscoveryError, match="AI Studio"):
        await discovery._gemini_med_sokning("hitta bolag")
