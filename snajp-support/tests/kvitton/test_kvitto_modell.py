"""KVITTO_MODEL och VERTEX_KVITTO_REGION (2026-11-18).

Kvittohanteraren (agenten och den andra kontrolläsningen i
`kvitton/hanterare.py`) ska kunna köra en annan modell och region än MODEL,
så att kvittostegen kan ligga kvar på gemini-2.5-flash i europe-west1 när
MODEL byts (kvittosviten: 30/40 på 3.5-flash-lite mot 37/40 på 2.5-flash,
`docs/compliance/modellbyte-underlag.md` avsnitt 6.4).

Osatta variabler ska ge exakt dagens beteende: MODEL på den vanliga
chattklienten. Regionen omfattas av INV-DATA-006 (testas i
`tests/invariants/test_inv_data_006.py`). Ingen modell anropas här.
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


@pytest.fixture
def miljo(monkeypatch):
    def nollstall():
        for namn in ("_llm_client", "_vision_client", "_embedding_client"):
            monkeypatch.setattr(llm, namn, None)
        monkeypatch.setattr(llm, "_regionklienter", {})
        get_settings.cache_clear()

    def satt(**env):
        for namn in ("KVITTO_MODEL", "VERTEX_KVITTO_REGION", "GOOGLE_CLOUD_REGION"):
            monkeypatch.delenv(namn, raising=False)
        for namn, varde in env.items():
            monkeypatch.setenv(namn, varde)
        nollstall()

    monkeypatch.setattr(llm, "_vertex_token", lambda _s: "fejktoken")
    yield satt
    nollstall()


def test_variablerna_ar_osatta_som_standard():
    s = Settings(_env_file=None)
    assert s.kvitto_model == ""
    assert s.vertex_kvitto_region == ""
    assert s.kvittomodell() == s.model
    assert s.kvittoregion() == s.google_cloud_region


def test_osatta_variabler_ger_samma_klient_som_forut(miljo):
    """Tom betyder dagens beteende: samma klientobjekt och MODEL."""
    miljo(LLM_PROVIDER="gemini", MODEL="gemini-3.5-flash-lite", GOOGLE_CLOUD_REGION="eu",
          ENVIRONMENT="lokal", GOOGLE_SERVICE_ACCOUNT_JSON=_SA_JSON)
    assert llm.get_kvitto_client() is llm.get_llm_client()
    assert get_settings().kvittomodell() == "gemini-3.5-flash-lite"


def test_satta_variabler_ger_egen_modell_och_region(miljo):
    """MODEL i `eu`, kvittostegen kvar på 2.5-flash i europe-west1."""
    miljo(LLM_PROVIDER="gemini", MODEL="gemini-3.5-flash-lite", GOOGLE_CLOUD_REGION="eu",
          ENVIRONMENT="main", GOOGLE_SERVICE_ACCOUNT_JSON=_SA_JSON,
          KVITTO_MODEL="gemini-2.5-flash", VERTEX_KVITTO_REGION="europe-west1")
    s = get_settings()
    assert s.llm_provider_fault() is None
    assert s.kvittomodell() == "gemini-2.5-flash"
    klient = llm.get_kvitto_client()
    assert klient is not llm.get_llm_client()
    assert urlsplit(str(klient.base_url)).hostname == "europe-west1-aiplatform.googleapis.com"


def test_kvittomodell_fran_fel_leverantor_faller_uppstarten():
    s = Settings(_env_file=None, llm_provider="gemini", model="gemini-2.5-flash",
                 google_service_account_json=_SA_JSON, kvitto_model="gpt-4o-mini")
    fel = s.llm_provider_fault()
    assert fel is not None and "KVITTO_MODEL" in fel


@pytest.mark.anyio
async def test_kontrollasningen_anvander_kvittomodellen(miljo, monkeypatch):
    """`_kontrollas` skickar KVITTO_MODEL till kvittoklienten och skriver
    modellnamnet i spåret."""
    from app.agent.step_runner import RunTrace
    from app.kvitton import hanterare

    miljo(LLM_PROVIDER="gemini", MODEL="gemini-3.5-flash-lite", ENVIRONMENT="lokal",
          GOOGLE_SERVICE_ACCOUNT_JSON=_SA_JSON, KVITTO_MODEL="gemini-2.5-flash")
    anrop: dict = {}

    class _Svar:
        usage = None

        class _Val:
            class message:  # noqa: N801
                content = '{"underlag": []}'

        choices = [_Val()]

    class _Komp:
        async def create(self, **kw):
            anrop.update(kw)
            return _Svar()

    class _Klient:
        class chat:  # noqa: N801
            completions = _Komp()

    monkeypatch.setattr(llm, "get_kvitto_client", lambda: _Klient())
    trace = RunTrace()
    rat = await hanterare._kontrollas("system", "underlag", trace)
    assert rat == {"underlag": []}
    assert anrop["model"] == "gemini-2.5-flash"
    assert trace.steps[-1].model == "gemini-2.5-flash"


@pytest.fixture
def anyio_backend():
    return "asyncio"
