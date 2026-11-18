"""Bytet från gemini-2.5 (pensionsdatum 2026-10-20) är en ändring av variabler,
inte av kod. Underlag: docs/compliance/modellbyte-underlag.md.

Det här låser det som annars hade krävt en kodändring den dag ägaren byter:

  * gemini-3.x godtas av uppstartskontrollen, i MODEL och i stegmodellerna,
    och ett namn från fel leverantör fälls i varje modellfält.
  * Tänkandet: gemini-3.x tar ingen tankebudget (avvecklad, gav ett anrop som
    hängde i 90 s mot gemini-3.8-flash) och gemini-3.8-flash avvisar MINIMAL
    (400), så "none" blir modellens lägsta nivå. gemini-2.5 är oförändrad.
  * Regionen: gemini-3.x finns i EU bara i multiregionen `eu` (värden
    aiplatform.eu.rep.googleapis.com) och, för gemini-3.5-flash, i
    europe-west3. Inbäddningsmodellen saknas i `eu` och har en egen region.
  * Standardvärdena är orörda: MODEL-defaulten, regionen och bildmodellen.
"""

from __future__ import annotations

import json
from urllib.parse import urlsplit

import pytest

from app.agent import llm
from app.config import Settings, get_settings, provider_for_model

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
_KANDIDATER = ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite"]


def _vertex(**kwargs) -> Settings:
    return Settings(
        _env_file=None,
        llm_provider="gemini",
        google_service_account_json=_SA_JSON,
        environment="main",
        **{"model": "gemini-2.5-flash", **kwargs},
    )


# -- Standardvärdena är orörda ---------------------------------------------------


def test_standardvardena_ar_ororda():
    s = Settings(_env_file=None, llm_provider="gemini")
    assert s.model == "gemini-2.5-flash"
    assert s.vision_model == "gemini-2.5-flash"
    assert s.google_cloud_region == "europe-west1"
    assert s.vertex_reservregioner == "europe-west4,europe-north1"
    assert s.inbaddningsregion() == "europe-west1"
    assert s.gemini_reasoning_effort == "none"


# -- Uppstartskontrollen ----------------------------------------------------------


@pytest.mark.parametrize("modell", _KANDIDATER)
def test_gemini3_godtas_i_varje_modellfalt(modell):
    assert provider_for_model(modell) == "gemini"
    for falt in ("model", "leads_draft_model", "leads_humanizer_model", "iris_profil_model", "vision_model"):
        assert _vertex(**{falt: modell}, google_cloud_region="eu").llm_provider_fault() is None, falt


@pytest.mark.parametrize("falt", ["leads_draft_model", "leads_humanizer_model", "iris_profil_model"])
def test_stegmodell_fran_fel_leverantor_faller_uppstarten(falt):
    fel = _vertex(**{falt: "deepseek-v4-flash"}).llm_provider_fault()
    assert fel is not None and falt.upper() in fel


def test_bildmodellen_maste_vara_gemini():
    fel = _vertex(vision_model="gpt-4o").llm_provider_fault()
    assert fel is not None and "VISION_MODEL" in fel


# -- Tänkandet ----------------------------------------------------------------------


def _niva(kwargs: dict) -> str | None:
    return kwargs.get("extra_body", {}).get("extra_body", {}).get("google", {}).get("thinking_config", {}).get(
        "thinking_level"
    )


def test_gemini25_ar_oforandrad():
    assert llm.gemini_tank_kwargs(None, "none", "gemini-2.5-flash") == llm.TANKANDE_AV
    assert llm.gemini_tank_kwargs(None, "none") == llm.TANKANDE_AV
    assert llm.gemini_tank_kwargs(None, "minimal", "gemini-2.5-flash") == {"reasoning_effort": "minimal"}


@pytest.mark.parametrize(
    "modell,niva",
    [
        ("gemini-3.5-flash", "MINIMAL"),
        ("gemini-3.5-flash-lite", "MINIMAL"),
        ("google/gemini-3.5-flash", "MINIMAL"),
        ("gemini-3.8-flash", "LOW"),
        ("google/gemini-3.8-flash", "LOW"),
    ],
)
def test_gemini3_far_lagsta_nivan_aldrig_tankebudget(modell, niva):
    kwargs = llm.gemini_tank_kwargs(None, "none", modell)
    assert _niva(kwargs) == niva
    assert "thinking_budget" not in json.dumps(kwargs)


def test_minimal_blir_low_dar_minimal_avvisas():
    assert llm.gemini_tank_kwargs(None, "minimal", "gemini-3.8-flash") == {"reasoning_effort": "low"}
    assert llm.gemini_tank_kwargs(None, "minimal", "gemini-3.5-flash") == {"reasoning_effort": "minimal"}
    assert llm.gemini_tank_kwargs(None, "high", "gemini-3.8-flash") == {"reasoning_effort": "high"}


def test_steg_som_vill_tanka_far_leverantorens_default():
    assert llm.gemini_tank_kwargs("enabled", "none", "gemini-3.8-flash") == {}


def test_sokningens_tankande_per_generation():
    from app.leads.discovery import _sokningens_tankande

    assert _sokningens_tankande("gemini-2.5-flash") == {"thinkingBudget": 0}
    assert _sokningens_tankande("gemini-3.5-flash") == {"thinkingLevel": "MINIMAL"}
    assert _sokningens_tankande("gemini-3.8-flash") == {"thinkingLevel": "LOW"}


# -- Regionerna -------------------------------------------------------------------


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


def test_eu_multiregionen_far_rep_vard(miljo):
    miljo(LLM_PROVIDER="gemini", MODEL="gemini-3.8-flash", ENVIRONMENT="main",
          GOOGLE_SERVICE_ACCOUNT_JSON=_SA_JSON, GOOGLE_CLOUD_REGION="eu", VERTEX_RESERVREGIONER="eu")
    bas = str(llm.get_llm_client().base_url)
    assert urlsplit(bas).hostname == "aiplatform.eu.rep.googleapis.com"
    assert "/locations/eu/endpoints/openapi/" in bas


def test_inbaddningen_har_egen_region(miljo):
    miljo(LLM_PROVIDER="gemini", MODEL="gemini-3.8-flash", ENVIRONMENT="main",
          GOOGLE_SERVICE_ACCOUNT_JSON=_SA_JSON, GOOGLE_CLOUD_REGION="eu",
          VERTEX_INBADDNING_REGION="europe-west1")
    assert get_settings().inbaddningsregion() == "europe-west1"
    assert urlsplit(str(llm.get_embedding_client().base_url)).hostname == "europe-west1-aiplatform.googleapis.com"
    assert urlsplit(str(llm.get_llm_client().base_url)).hostname == "aiplatform.eu.rep.googleapis.com"


@pytest.mark.anyio
async def test_inbaddningsanropet_gar_till_sin_region(miljo, monkeypatch):
    from app.agent import embeddings

    miljo(LLM_PROVIDER="gemini", MODEL="gemini-3.8-flash", ENVIRONMENT="lokal",
          GOOGLE_SERVICE_ACCOUNT_JSON=_SA_JSON, GOOGLE_CLOUD_REGION="eu",
          VERTEX_INBADDNING_REGION="europe-west3")
    sedda: list[str] = []

    class _Svar:
        def raise_for_status(self):
            return None

        def json(self):
            return {"predictions": [{"embeddings": {"values": [0.0] * 3}}]}

    class _Klient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, **kwargs):
            sedda.append(url)
            return _Svar()

    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", _Klient)
    await embeddings._vertex_predict(get_settings(), "text")
    assert urlsplit(sedda[0]).hostname == "europe-west3-aiplatform.googleapis.com"
    assert "/locations/europe-west3/" in sedda[0]


@pytest.fixture
def anyio_backend():
    return "asyncio"
