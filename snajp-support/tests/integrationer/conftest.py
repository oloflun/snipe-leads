"""Gemensamt för integrationstesterna: hermetiskt nät.

Vakten (natvakt.VaktadTransport) ligger kvar i varje test — det är den som
ska provas. Det som byts är det UNDER den: DNS-uppslaget och den inre
transporten. Ett test som glömmer att sätta en transport får ett tydligt fel
i stället för ett riktigt nätverksanrop.
"""

from __future__ import annotations

import httpx
import pytest

from app.integrationer import mcp_klient, natvakt

PUBLIK_IP = "93.184.216.34"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _hermetiskt_nat(monkeypatch):
    async def falsk_dns(vard: str, port: int) -> list[str]:
        return [PUBLIK_IP]

    def ingen_transport() -> httpx.AsyncBaseTransport:
        def vagra(request: httpx.Request) -> httpx.Response:
            raise AssertionError(f"Testet gjorde ett oväntat anrop till {request.url}")

        return httpx.MockTransport(vagra)

    monkeypatch.setattr(natvakt, "upplos", falsk_dns)
    monkeypatch.setattr(natvakt, "inre_transport", ingen_transport)
    mcp_klient.tom_cache()
    yield
    mcp_klient.tom_cache()


@pytest.fixture
def svara(monkeypatch):
    """svara(hanterare) — låter en httpx.MockTransport-hanterare svara på allt.

    Returnerar listan med mottagna förfrågningar, för kontroller i efterhand.
    """

    def satt(hanterare):
        mottagna: list[httpx.Request] = []

        def inre(request: httpx.Request) -> httpx.Response:
            mottagna.append(request)
            return hanterare(request)

        monkeypatch.setattr(natvakt, "inre_transport", lambda: httpx.MockTransport(inre))
        return mottagna

    return satt
