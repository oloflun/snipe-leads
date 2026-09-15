"""Webbplatsgissningen följer bara en redirect till bolagets egen domän.

Uppmätt 2026-09-15 i QA-kundens leadskörning: "EdZa AB" fick
http://home.student.uu.se/edza0987 som webbplats. edza.se svarade med en
redirect dit, och kontrollen godtog den för att slugen stod i SÖKVÄGEN.
"""

from __future__ import annotations

import httpx
import pytest

from app.leads import discovery

_RIKTIG_ASYNC_CLIENT = httpx.AsyncClient


def _med_redirects(monkeypatch, platser: dict[str, str]):
    def handler(request):
        url = str(request.url).rstrip("/")
        if url in platser:
            return httpx.Response(301, headers={"location": platser[url]})
        return httpx.Response(404)

    def fabrik(**kwargs):
        return _RIKTIG_ASYNC_CLIENT(transport=httpx.MockTransport(handler))

    monkeypatch.setattr(discovery.httpx, "AsyncClient", fabrik)


@pytest.mark.anyio
async def test_redirect_till_annan_vard_med_slugen_i_sokvagen_ar_ingen_traff(monkeypatch):
    student = "http://home.student.uu.se/edza0987"
    _med_redirects(
        monkeypatch,
        {"https://edza.se": student, "https://www.edza.se": student, "http://edza.se": student},
    )
    assert await discovery.gissa_webbplats_via_head("EdZa AB") is None


@pytest.mark.anyio
async def test_redirect_inom_bolagets_egen_doman_godtas(monkeypatch):
    _med_redirects(monkeypatch, {"https://nordkapmoduler.se": "https://www.nordkapmoduler.se/sv"})
    assert (
        await discovery.gissa_webbplats_via_head("Nordkap Moduler AB")
        == "https://www.nordkapmoduler.se/sv"
    )


@pytest.fixture
def anyio_backend():
    return "asyncio"
