"""INV-DATA-006: där data är riktig går modellanropen bara till Vertex AI i EU.

Tre vägar ut ur EU som ingen kod stängde (dataskyddsbedömningen av Gemini,
2026-11-18, avvikelse A3 till A5):

  * Regionen. `GOOGLE_CLOUD_REGION` och `VERTEX_RESERVREGIONER` lästes utan
    kontroll. `us-central1` eller `global` hade tyst flyttat behandlingen.
  * `LLM_BASE_URL` gick före all regionlogik och kunde peka vart som helst.
  * OpenAI var tillåtet med riktig kunddata, och är standardvärdet för
    `LLM_PROVIDER`. OpenAI står inte i underbiträdesförteckningen.

Samma gräns som DeepSeek-spärren och INV-DATA-004 (`har_riktig_kunddata`):
känt kunddatamiljönamn eller en databas utanför loopback. Lokalt och i
testsviten fungerar allt som förut.
"""

from __future__ import annotations

import json
from urllib.parse import urlsplit

import pytest

from app.agent import llm
from app.config import VERTEX_EU_REGIONER, Settings, get_settings

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

#: De fyra sätten processen kan veta att datan är riktig.
_RIKTIG = [
    {"environment": "main"},
    {"environment": "development"},
    {"railway_environment_name": "main"},
    {"database_url": _FJARR_DB},
]
_LOKAL = [{}, {"environment": "lokal"}, {"database_url": "postgresql://u:p@127.0.0.1:5432/x"}]


def _settings(**kwargs) -> Settings:
    return Settings(_env_file=None, **kwargs)


def _vertex(**kwargs) -> Settings:
    """Driftens form: gemini via servicekontot."""
    return _settings(
        llm_provider="gemini",
        model="gemini-2.5-flash",
        google_service_account_json=_SA_JSON,
        **kwargs,
    )


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def miljo(monkeypatch):
    def nollstall():
        for namn in ("_llm_client", "_vision_client", "_embedding_client"):
            monkeypatch.setattr(llm, namn, None)
        monkeypatch.setattr(llm, "_regionklienter", {})
        get_settings.cache_clear()

    def satt(**env):
        for namn, varde in env.items():
            monkeypatch.setenv(namn, varde)
        nollstall()

    monkeypatch.setattr(llm, "_vertex_token", lambda _s: "fejktoken")
    yield satt
    nollstall()


# -- Listan -------------------------------------------------------------------


def test_listan_bar_driftens_regioner_och_aldrig_global():
    standard = _settings()
    for region in [standard.google_cloud_region, *standard.vertex_reservregioner.split(",")]:
        assert region in VERTEX_EU_REGIONER, f"standardvärdet {region} står inte på EU-listan"
    for utanfor in ("global", "us", "us-central1", "europe-west2", "europe-west6", "eu"):
        assert utanfor not in VERTEX_EU_REGIONER


# -- (a) Regionen ---------------------------------------------------------------


def test_driftens_konfiguration_falls_inte():
    """Det som står i main och development i dag: gemini, servicekontot, inga
    regionvariabler (alltså standardvärdena), ingen LLM_BASE_URL."""
    for kwargs in _RIKTIG:
        assert _vertex(**kwargs).llm_provider_fault() is None


@pytest.mark.parametrize("kwargs", _RIKTIG)
@pytest.mark.parametrize("falt", [{"google_cloud_region": "us-central1"}, {"google_cloud_region": "global"},
                                  {"vertex_reservregioner": "europe-west4,us-east4"},
                                  {"vertex_reservregioner": "europe-west2"}])
def test_region_utanfor_eu_faller_uppstarten(kwargs, falt):
    fel = _vertex(**kwargs, **falt).llm_provider_fault()
    assert fel is not None
    assert "GOOGLE_CLOUD_REGION" in fel and "EU" in fel


@pytest.mark.parametrize("kwargs", _LOKAL)
def test_region_utanfor_eu_gar_lokalt(kwargs):
    assert _vertex(google_cloud_region="us-central1", **kwargs).llm_provider_fault() is None


def test_klientbygget_vagrar_en_reservregion_utanfor_eu(miljo):
    """Reservregionen skickas in vid anropet (step_runner vid 429), efter att
    uppstarten passerats. Klienten får inte byggas mot den."""
    miljo(LLM_PROVIDER="gemini", MODEL="gemini-2.5-flash", ENVIRONMENT="main", GOOGLE_SERVICE_ACCOUNT_JSON=_SA_JSON)
    assert urlsplit(str(llm.get_llm_client(region="europe-west4").base_url)).hostname == (
        "europe-west4-aiplatform.googleapis.com"
    )
    with pytest.raises(llm.ForbjudenProviderIMiljon, match="EU"):
        llm.get_llm_client(region="us-central1")


def test_klientbygget_tillater_annan_region_lokalt(miljo):
    miljo(LLM_PROVIDER="gemini", MODEL="gemini-2.5-flash", ENVIRONMENT="lokal", GOOGLE_SERVICE_ACCOUNT_JSON=_SA_JSON)
    assert urlsplit(str(llm.get_llm_client(region="us-central1").base_url)).hostname == (
        "us-central1-aiplatform.googleapis.com"
    )


@pytest.mark.anyio
async def test_inbaddningen_vagrar_region_utanfor_eu(miljo, monkeypatch):
    """Inbäddningen bygger sin egen adress (:predict) och passerar inte
    klientens bas-URL. Den får inte nå nätet med en region utanför EU."""
    from app.agent import embeddings

    def inget_natanrop(*args, **kwargs):
        raise AssertionError("inbäddningen anropade en region utanför EU")

    monkeypatch.setattr("httpx.AsyncClient", inget_natanrop)
    s = _vertex(environment="main", google_cloud_region="us-central1")
    with pytest.raises(llm.ForbjudenProviderIMiljon):
        await embeddings._vertex_predict(s, "text")


@pytest.mark.anyio
async def test_grundade_sokningen_vagrar_region_utanfor_eu(miljo, monkeypatch):
    from app.leads import discovery

    def inget_natanrop(*args, **kwargs):
        raise AssertionError("sökningen anropade en region utanför EU")

    monkeypatch.setattr(discovery.httpx, "AsyncClient", inget_natanrop)
    miljo(
        LLM_PROVIDER="gemini",
        MODEL="gemini-2.5-flash",
        DATABASE_URL=_FJARR_DB,
        GOOGLE_SERVICE_ACCOUNT_JSON=_SA_JSON,
        GOOGLE_CLOUD_REGION="us-central1",
    )
    with pytest.raises(discovery.DiscoveryError, match="EU"):
        await discovery._gemini_med_sokning("hitta bolag")


# -- (b) LLM_BASE_URL -----------------------------------------------------------


@pytest.mark.parametrize("kwargs", _RIKTIG)
@pytest.mark.parametrize(
    "url",
    [
        "https://api.openai.com/v1",
        "https://us-central1-aiplatform.googleapis.com/v1beta1/projects/p/locations/us-central1/endpoints/openapi/",
        "https://aiplatform.googleapis.com/v1/",
        # Värdnamnet jämförs exakt, inte som delsträng.
        "https://europe-west1-aiplatform.googleapis.com.exempel.se/",
        "http://europe-west1-aiplatform.googleapis.com/",
        "http://localhost:11434/v1",
    ],
)
def test_bas_url_utanfor_listan_faller_uppstarten(kwargs, url):
    fel = _vertex(llm_base_url=url, **kwargs).llm_provider_fault()
    assert fel is not None
    assert "LLM_BASE_URL" in fel


def test_bas_url_mot_vertex_i_eu_ar_tillaten():
    url = "https://europe-west4-aiplatform.googleapis.com/v1beta1/projects/p/locations/europe-west4/endpoints/openapi/"
    assert _vertex(llm_base_url=url, environment="main").llm_provider_fault() is None


@pytest.mark.parametrize("kwargs", _LOKAL)
def test_bas_url_fungerar_lokalt_som_forut(kwargs):
    s = _settings(llm_provider="openai", openai_api_key=_NYCKEL, llm_base_url="http://localhost:11434/v1", **kwargs)
    assert s.llm_provider_fault() is None
    assert llm._resolve_base_url(s) == "http://localhost:11434/v1"


def test_klientbygget_vagrar_bas_url_utanfor_listan():
    s = _vertex(environment="main", llm_base_url="https://api.openai.com/v1")
    with pytest.raises(llm.ForbjudenProviderIMiljon, match="LLM_BASE_URL"):
        llm._resolve_base_url(s)


# -- (c) OpenAI -----------------------------------------------------------------


@pytest.mark.parametrize("kwargs", _RIKTIG)
def test_openai_vagras_dar_data_ar_riktig(kwargs):
    fel = _settings(llm_provider="openai", openai_api_key=_NYCKEL, **kwargs).llm_provider_fault()
    assert fel is not None
    assert "openai" in fel.lower()
    assert "avtalsbeslut" in fel


def test_standardvardet_openai_vagras_dar_data_ar_riktig():
    """LLM_PROVIDER osatt betyder openai. En riktig miljö som glömt variabeln
    ska dö högljutt, inte tyst skicka kundmejl till USA."""
    assert _settings(environment="main").llm_provider_fault() is not None


@pytest.mark.parametrize("kwargs", _LOKAL)
def test_openai_gar_lokalt(kwargs):
    assert _settings(llm_provider="openai", openai_api_key=_NYCKEL, **kwargs).llm_provider_fault() is None


def test_chattklienten_vagrar_openai_dar_data_ar_riktig(miljo):
    miljo(LLM_PROVIDER="openai", MODEL="gpt-4o-mini", OPENAI_API_KEY=_NYCKEL, ENVIRONMENT="development")
    with pytest.raises(llm.ForbjudenProviderIMiljon, match="openai"):
        llm.get_llm_client()


@pytest.mark.anyio
async def test_lifespan_dor_med_openai_i_riktig_miljo(miljo):
    from app.main import app, lifespan

    miljo(LLM_PROVIDER="openai", MODEL="gpt-4o-mini", OPENAI_API_KEY=_NYCKEL, ENVIRONMENT="main")
    with pytest.raises(RuntimeError, match="avtalsbeslut"):
        async with lifespan(app):
            pass
