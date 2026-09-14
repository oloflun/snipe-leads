"""Vertex openapi-endpoint vill ha `google/<modell>` — och får det.

Uppmätt 2026-09-14 mot båda miljöernas service account: bart
`gemini-2.5-flash` mot `endpoints/openapi/` svarar

    400 Malformed publisher model (`model`: 'gemini-2.5-flash') for the
    'openapi' request endpoint ID; expected '<publisher>/<model>'.

Varje agentanrop hade fallit sedan flytten till Vertex, medan /health/ready
svarade `mode: live`. Testerna nedan kör genom en RIKTIG AsyncOpenAI mot en
mockad transport och läser modellnamnet ur den HTTP-kropp som faktiskt hade
lämnat processen — inte ur ett argument till en mock. Det är skillnaden mellan
att testa att vi SKICKAR prefixet och att testa att SDK:n inte tappar det.
"""

from __future__ import annotations

import json

import httpx
import pytest
from openai import AsyncOpenAI

from app.agent import llm
from app.agent.llm import _med_vertex_modellnamn, vertex_modellnamn
from app.config import get_settings

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

_SVAR = {
    "id": "x",
    "object": "chat.completion",
    "created": 0,
    "model": "google/gemini-2.5-flash",
    "choices": [
        {"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": "ok"}}
    ],
}


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _klient_som_spelar_in(kroppar: list[dict]) -> AsyncOpenAI:
    def svara(request: httpx.Request) -> httpx.Response:
        kroppar.append(json.loads(request.content))
        return httpx.Response(200, json=_SVAR)

    return AsyncOpenAI(
        api_key="tok",
        base_url="https://europe-west1-aiplatform.googleapis.com/v1beta1/projects/test-proj/locations/europe-west1/endpoints/openapi/",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(svara)),
        max_retries=0,
    )


# -- Den rena funktionen -------------------------------------------------------


@pytest.mark.parametrize(
    "in_, ut",
    [
        ("gemini-2.5-flash", "google/gemini-2.5-flash"),
        ("  gemini-2.5-pro ", "google/gemini-2.5-pro"),
        ("google/gemini-2.5-flash", "google/gemini-2.5-flash"),  # aldrig google/google/
        ("meta/llama-4", "meta/llama-4"),  # en satt publisher är ett beslut
        ("", ""),
    ],
)
def test_vertex_modellnamn(in_, ut):
    assert vertex_modellnamn(in_) == ut


# -- Genom SDK:n, till tråden --------------------------------------------------


@pytest.mark.anyio
async def test_prefixet_nar_http_kroppen():
    kroppar: list[dict] = []
    klient = _med_vertex_modellnamn(_klient_som_spelar_in(kroppar))

    await klient.chat.completions.create(
        model="gemini-2.5-flash",
        messages=[{"role": "user", "content": "ok"}],
        response_format={"type": "json_object"},
        temperature=0.3,
    )

    assert kroppar[0]["model"] == "google/gemini-2.5-flash"
    # Resten av kroppen är orörd — prefixet får inte ta med sig något annat.
    assert kroppar[0]["response_format"] == {"type": "json_object"}
    assert kroppar[0]["temperature"] == 0.3


@pytest.mark.anyio
async def test_omslutning_ar_idempotent():
    """En cache som läses om får inte ge google/google/…"""
    kroppar: list[dict] = []
    klient = _klient_som_spelar_in(kroppar)
    _med_vertex_modellnamn(klient)
    _med_vertex_modellnamn(klient)

    await klient.chat.completions.create(model="gemini-2.5-flash", messages=[{"role": "user", "content": "ok"}])
    assert kroppar[0]["model"] == "google/gemini-2.5-flash"


@pytest.mark.anyio
async def test_agents_sdk_far_prefixet_via_samma_klient():
    """Bokföringschatten kör Agents SDK. Den anropar
    `self._get_client().chat.completions.create(**kwargs)` — samma objekt som
    omslutits, alltså samma prefix."""
    from agents import OpenAIChatCompletionsModel

    kroppar: list[dict] = []
    klient = _med_vertex_modellnamn(_klient_som_spelar_in(kroppar))
    modell = OpenAIChatCompletionsModel(model="gemini-2.5-flash", openai_client=klient)

    assert modell._get_client().chat.completions.create is klient.chat.completions.create


# -- Klientbygget: prefix bara mot Vertex --------------------------------------


def _nollstall_klienter(monkeypatch):
    monkeypatch.setattr(llm, "_llm_client", None)
    monkeypatch.setattr(llm, "_vision_client", None)
    get_settings.cache_clear()


@pytest.mark.anyio
async def test_get_llm_client_omsluter_mot_vertex(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("MODEL", "gemini-2.5-flash")
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", _SA_JSON)
    monkeypatch.setenv("ENVIRONMENT", "lokal")
    _nollstall_klienter(monkeypatch)
    monkeypatch.setattr(llm, "_vertex_token", lambda _s: "tok")
    try:
        klient = llm.get_llm_client()
        assert getattr(klient.chat.completions.create, "_vertex_modellnamn", False)
        vision = llm.get_vision_client()
        assert getattr(vision.chat.completions.create, "_vertex_modellnamn", False)
    finally:
        _nollstall_klienter(monkeypatch)


@pytest.mark.anyio
async def test_get_llm_client_rör_inte_ai_studio_eller_openai(monkeypatch):
    """AI Studios endpoint (GEMINI_API_KEY) vill ha BART namn — ett prefix där
    hade brutit den reservvägen."""
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("MODEL", "gpt-4o-mini")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-inte-en-riktig-nyckel-000000")
    monkeypatch.delenv("GOOGLE_SERVICE_ACCOUNT_JSON", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "lokal")
    _nollstall_klienter(monkeypatch)
    try:
        klient = llm.get_llm_client()
        assert not getattr(klient.chat.completions.create, "_vertex_modellnamn", False)
    finally:
        _nollstall_klienter(monkeypatch)
