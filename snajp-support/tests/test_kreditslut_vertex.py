"""Kreditslut via Vertex AI: samma permanenta sanning, ny formulering.

Testarens fynd 2026-09-13: chatten sa "försök igen" när AI-kapaciteten tagit
slut. Två orsaker, båda vaktade här:

  1. Klassaren kände bara igen AI Studios förskottskredit ("prepayment
     credits are depleted", 429). Sedan miljön flyttade till Vertex AI (commit
     b1a651e) svarar ett tomt/stängt faktureringskonto 403 PERMISSION_DENIED
     med BILLING_DISABLED — inget 429, ingen markör — och felet föll ned till
     den generiska "prova igen"-meningen utan larm.
  2. chat.py sniffade "RateLimit"/"429" i råtexten i stället för att fråga
     kvotfel.ar_kvotfel, och SupportChat.tsx kastade bort backendens text vid
     status "failed" (frontenddelen verifieras med tsc; backenddelen här).

Payloaderna nedan byggs av openai-SDK:ns EGEN felkonstruktion mot ett
httpx-svar, så strängformen är den som faktiskt når chat.py — inte en
handskriven gissning.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.kvotfel import (
    KUNDTEXT_KREDITSLUT,
    KUNDTEXT_KVOT,
    ar_kreditslut,
    ar_kvotfel,
    kundtext_for,
    oversatt_felstext,
)

_VERTEX_URL = (
    "https://europe-north1-aiplatform.googleapis.com/v1beta1/projects/snajp-prod/"
    "locations/europe-north1/endpoints/openapi/chat/completions"
)

#: Googles svar när faktureringen är avstängd på projektet.
VERTEX_BILLING_DISABLED = [
    {
        "error": {
            "code": 403,
            "message": (
                "This API method requires billing to be enabled. Please enable billing "
                "on project #123456789012 by visiting https://console.developers.google"
                ".com/billing/enable?project=123456789012 then retry. If you enabled "
                "billing for this project recently, wait a few minutes for the action "
                "to propagate to our systems and retry."
            ),
            "status": "PERMISSION_DENIED",
            "details": [
                {
                    "@type": "type.googleapis.com/google.rpc.ErrorInfo",
                    "reason": "BILLING_DISABLED",
                    "domain": "googleapis.com",
                    "metadata": {"service": "aiplatform.googleapis.com"},
                }
            ],
        }
    }
]

#: Faktureringskontot stängt (t.ex. slut testperiod/krediter på kontot).
VERTEX_KONTO_STANGT = [
    {
        "error": {
            "code": 403,
            "message": (
                "The billing account for the owning project is disabled in state closed"
            ),
            "status": "PERMISSION_DENIED",
        }
    }
]

#: Projektet avstängt.
VERTEX_AVSTANGT = [
    {
        "error": {
            "code": 403,
            "message": "Consumer 'projects/123456789012' has been suspended.",
            "status": "PERMISSION_DENIED",
            "details": [
                {
                    "@type": "type.googleapis.com/google.rpc.ErrorInfo",
                    "reason": "CONSUMER_SUSPENDED",
                }
            ],
        }
    }
]

#: Vertex minutkvot — ÖVERGÅENDE. Notera: inget "quota" i texten.
VERTEX_MINUTKVOT = [
    {
        "error": {
            "code": 429,
            "message": (
                "Resource exhausted. Please try again later. Please refer to "
                "https://cloud.google.com/vertex-ai/generative-ai/docs/error-code-429 "
                "for more details."
            ),
            "status": "RESOURCE_EXHAUSTED",
        }
    }
]


def _sdkfel(status: int, body) -> Exception:
    """Felet exakt som AsyncOpenAI kastar det för ett HTTP-svar."""
    from openai import AsyncOpenAI

    klient = AsyncOpenAI(api_key="test-key-not-a-real-credential-000000", base_url=_VERTEX_URL)
    svar = httpx.Response(status, json=body, request=httpx.Request("POST", _VERTEX_URL))
    return klient._make_status_error_from_response(svar)


@pytest.fixture
def anyio_backend():
    return "asyncio"


# -- Klassningen ------------------------------------------------------------


@pytest.mark.parametrize("body", [VERTEX_BILLING_DISABLED, VERTEX_KONTO_STANGT, VERTEX_AVSTANGT])
def test_vertex_betalningsfel_ar_kreditslut(body):
    fel = _sdkfel(403, body)
    assert fel.status_code == 403
    assert ar_kreditslut(fel)
    assert kundtext_for(fel) == KUNDTEXT_KREDITSLUT
    # Den lagrade feltexten (jobbläsvägen) klassas likadant.
    assert oversatt_felstext(str(fel)) == KUNDTEXT_KREDITSLUT


def test_vertex_minutkvot_ar_overgaende_inte_kreditslut():
    """Skillnaden bär åtgärden: minutkvoten väntas ut, betalningsfelet inte.
    Vertex text saknar ordet 'quota' — RESOURCE_EXHAUSTED måste räcka."""
    fel = _sdkfel(429, VERTEX_MINUTKVOT)
    assert ar_kvotfel(fel)
    assert not ar_kreditslut(fel)
    assert kundtext_for(fel) == KUNDTEXT_KVOT
    # Även utan statuskod-attributet (lagrad text, omslaget fel).
    assert ar_kvotfel(Exception(str(fel)))
    assert oversatt_felstext(str(fel)) == KUNDTEXT_KVOT


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("status", "body", "kredit"),
    [(403, VERTEX_BILLING_DISABLED, True), (429, VERTEX_MINUTKVOT, False)],
)
async def test_discovery_bar_leverantorens_svar_i_orsaken(monkeypatch, status, body, kredit):
    """discovery.py kastade bort svarskroppen vid 4xx, så ett kreditslut mitt i
    en leadssökning gav "försök igen" och inget larm. Svaret ska nu ligga i
    ORSAKEN — klassarna ser det — medan meddelandet självt är oförändrat."""
    from app.config import get_settings
    from app.leads import discovery

    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("MODEL", "gemini-2.5-flash")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-a-real-credential-000000")
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    get_settings.cache_clear()

    async def avvisa(self, url, **kwargs):
        return httpx.Response(status, json=body, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", avvisa)
    try:
        with pytest.raises(discovery.DiscoveryError) as fangat:
            await discovery._gemini_med_sokning("hitta bolag")
    finally:
        get_settings.cache_clear()

    fel = fangat.value
    assert str(fel) == f"Sokningen avvisades ({status})."
    assert ar_kreditslut(fel) is kredit
    assert ar_kvotfel(fel) is (not kredit)


def test_omslaget_fel_klassas_genom_kedjan():
    """Ett eget undantag ovanpå leverantörens ('raise X from fel') bär
    diagnosen i orsaken. Klassaren ska inte bli blind av omslaget."""
    kredit = _sdkfel(403, VERTEX_BILLING_DISABLED)
    kvot = _sdkfel(429, VERTEX_MINUTKVOT)
    try:
        try:
            raise kredit
        except Exception as inre:
            raise RuntimeError("Sokningen avvisades (403).") from inre
    except RuntimeError as yttre:
        assert ar_kreditslut(yttre)
    try:
        try:
            raise kvot
        except Exception as inre:
            raise RuntimeError("omslag") from inre
    except RuntimeError as yttre:
        assert ar_kvotfel(yttre)
        assert not ar_kreditslut(yttre)


@pytest.mark.parametrize(
    "fel",
    [
        RuntimeError("429 kr exklusive moms"),
        ValueError("Prospektet saknar mottagaradress."),
        _sdkfel(403, [{"error": {"code": 403, "message": "Permission denied on resource "
                                 "project snajp-prod.", "status": "PERMISSION_DENIED"}}]),
    ],
)
def test_andra_fel_klassas_inte_som_kvot_eller_kredit(fel):
    """Ett 403 för en felkonfigurerad IAM-roll är VÅRT fel, inte en kredit —
    det ska inte larma som kreditslut eller visas som 'vi fyller på'."""
    assert not ar_kreditslut(fel)
    assert not ar_kvotfel(fel)
    assert kundtext_for(fel) is None


# -- Chattens felväg --------------------------------------------------------


async def _kor_chatt_som_kastar(fel: Exception, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-a-real-credential-000000")
    from app.api.chat import _process
    from app.api.schemas import ChatRequest
    from app.config import get_settings
    from app.jobs.store import MemoryJobStore
    from app.storage.memory import MemoryStorage

    get_settings.cache_clear()
    storage = MemoryStorage()
    jobs = MemoryJobStore()
    app_state = SimpleNamespace(storage=storage, jobs=jobs)
    job_id = await jobs.create(tenant_id="t-1")
    request = ChatRequest(message="Hej!", channel="web", customer_email="kund@example.com")
    try:
        with (
            patch(
                "app.agent.support_agent.run_support_agent", new=AsyncMock(side_effect=fel)
            ),
            patch("app.api.chat.larma_kreditslut", new=AsyncMock()) as larm,
        ):
            await _process(app_state, job_id, "t-1", request, attachments=[])
    finally:
        get_settings.cache_clear()
    return await jobs.get(job_id), larm


@pytest.mark.anyio
async def test_chatten_ger_kredittext_och_larmar_vid_vertex_billing(monkeypatch):
    job, larm = await _kor_chatt_som_kastar(_sdkfel(403, VERTEX_BILLING_DISABLED), monkeypatch)
    assert job["status"] == "failed"
    assert job["error"] == KUNDTEXT_KREDITSLUT
    assert "försök igen" not in job["error"].casefold()
    larm.assert_awaited_once()
    assert larm.await_args.kwargs["kalla"] == "chat"


@pytest.mark.anyio
async def test_chatten_ger_kvottext_for_omslaget_minutkvot(monkeypatch):
    """Den gamla sniffen ('429' bland de första 80 tecknen) missade ett
    omslaget kvotfel och gav den generiska meningen."""
    kvot = _sdkfel(429, VERTEX_MINUTKVOT)
    omslag = RuntimeError("agentsteget föll")
    omslag.__cause__ = kvot
    job, larm = await _kor_chatt_som_kastar(omslag, monkeypatch)
    assert job["error"] == KUNDTEXT_KVOT
    larm.assert_not_awaited()


@pytest.mark.anyio
async def test_chatten_tar_inte_ett_belopp_for_en_kvot(monkeypatch):
    job, _ = await _kor_chatt_som_kastar(RuntimeError("429 kr saknas i kassan"), monkeypatch)
    assert job["error"] not in (KUNDTEXT_KVOT, KUNDTEXT_KREDITSLUT)
    assert "429 kr" not in job["error"]
