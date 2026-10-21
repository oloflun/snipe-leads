"""Den grounded sökningens anropskropp måste bära role - Vertex kräver det.

Uppmätt 2026-09-15 mot Vertex med development-miljöns service account:
samma kropp utan "role" gav 400 "Please use a valid role: user, model.",
med "role": "user" 200 inklusive groundingMetadata. AI Studio accepterar
båda, så felet syntes aldrig före flytten till Vertex.
"""

from __future__ import annotations

import pytest

from app.leads import discovery


class _Settings:
    model = "gemini-2.5-flash"
    google_cloud_region = "europe-west1"

    def __init__(self, *, vertex: bool):
        self.google_service_account_json = '{"project_id": "fejkprojekt"}' if vertex else ""
        self.gemini_api_key = "fejk-" + "a" * 20

    def active_llm_key(self) -> str:
        return self.gemini_api_key


class _Svar:
    status_code = 200
    text = ""

    def json(self):
        return {"candidates": [{"content": {"parts": [{"text": "[]"}]}}]}


def _fanga(monkeypatch, *, vertex: bool) -> dict:
    fangat: dict = {}

    class _Klient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, **kwargs):
            fangat["url"] = url
            fangat["kropp"] = kwargs["json"]
            return _Svar()

    monkeypatch.setattr(discovery, "get_settings", lambda: _Settings(vertex=vertex))
    monkeypatch.setattr(discovery.httpx, "AsyncClient", _Klient)
    monkeypatch.setattr("app.agent.llm._vertex_token", lambda settings: "fejktoken")
    return fangat


@pytest.mark.anyio
@pytest.mark.parametrize("vertex", [True, False])
async def test_sokningens_innehall_bar_rollen_user(monkeypatch, vertex):
    fangat = _fanga(monkeypatch, vertex=vertex)
    assert await discovery._gemini_med_sokning("hitta bolag") == "[]"
    innehall = fangat["kropp"]["contents"]
    assert [del_["role"] for del_ in innehall] == ["user"]
    assert fangat["kropp"]["tools"] == [{"google_search": {}}]
    # 2026-09-15: med tänkande tog sökningen 258–300+ s, utan 9–16 s.
    assert fangat["kropp"]["generationConfig"]["thinkingConfig"] == {"thinkingBudget": 0}
    if vertex:
        assert "aiplatform.googleapis.com" in fangat["url"]
        assert "/publishers/google/models/gemini-2.5-flash:generateContent" in fangat["url"]


@pytest.mark.anyio
async def test_ai_studio_far_aldrig_en_borttagen_modell(monkeypatch):
    """AI Studio drog tillbaka gemini-2.5-serien (404 "no longer available
    ... use models/gemini-3.8-flash", uppmätt 2026-10-21 med både main- och
    dev-nyckeln): varje grounded sökning på den vägen föll, och körningarna
    i main slutade som "inga träffar". Vertex-grenen behåller kundens modell
    — europe-west1 har kvar 2.5 och saknar 3.8 (BESLUT 2026-10-16)."""
    fangat = _fanga(monkeypatch, vertex=False)
    await discovery._gemini_med_sokning("hitta bolag")
    assert "/models/gemini-3.8-flash:generateContent" in fangat["url"]

    fangat = _fanga(monkeypatch, vertex=True)
    await discovery._gemini_med_sokning("hitta bolag")
    assert "/models/gemini-2.5-flash:generateContent" in fangat["url"]
