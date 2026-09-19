"""/api/integrationer: CRUD, maskerade hemligheter, provkörning."""

from __future__ import annotations

import httpx
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.integrationer import router
from app.config import get_settings
from app.integrationer import lagring
from app.storage.memory import MemoryStorage

NYCKEL = {"X-API-Key": get_settings().snajp_demo_api_key}

ORDER = {
    "requests": [
        {
            "name": "Orderstatus",
            "description": "Status för en order.",
            "url": "https://shop.example.com/orders/{{ordernummer}}",
            "headers": {"Authorization": "Bearer {{hemlighet.token}}"},
        },
        {
            "name": "Avboka",
            "method": "POST",
            "url": "https://shop.example.com/orders/{{ordernummer}}/cancel",
            "headers": {"Authorization": "Bearer {{hemlighet.token}}"},
        },
    ]
}


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(router)
    app.state.storage = MemoryStorage()
    return app


def _klient(app):
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=NYCKEL)


@pytest.mark.anyio
async def test_krav_pa_nyckel(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as k:
        assert (await k.get("/api/integrationer")).status_code == 401


@pytest.mark.anyio
async def test_skapa_lista_andra_ta_bort_utan_att_lacka_hemligheter(app):
    async with _klient(app) as k:
        skapad = await k.post(
            "/api/integrationer",
            json={"typ": "http", "namn": "Butiken", "konfig": ORDER, "hemligheter": {"token": "sk_live_abcdef123"}},
        )
        assert skapad.status_code == 201, skapad.text
        data = skapad.json()
        assert data["hemligheter"] == {"token": "[hemlighet]"}
        assert "sk_live_abcdef123" not in skapad.text

        lista = await k.get("/api/integrationer")
        assert lista.status_code == 200
        assert "sk_live_abcdef123" not in lista.text
        assert "hemligheter_krypterat" not in lista.text
        assert "arende_eskalerat" in lista.json()["handelser"]

        # I vila är hemligheten krypterad, inte klartext.
        rad = await lagring.hamta(app.state.storage, "00000000-0000-4000-a000-000000000001", data["id"])
        assert "sk_live_abcdef123" not in (rad["hemligheter_krypterat"] or "")
        assert lagring.dekryptera_hemligheter(rad) == {"token": "sk_live_abcdef123"}

        # En ändring som inte nämner hemligheter behåller dem.
        andrad = await k.patch(f"/api/integrationer/{data['id']}", json={"beskrivning": "Webbutiken"})
        assert andrad.status_code == 200 and andrad.json()["hemligheter"] == {"token": "[hemlighet]"}

        # Att ta bort en hemlighet som konfigurationen använder avvisas.
        utan = await k.patch(f"/api/integrationer/{data['id']}", json={"hemligheter": {"token": None}})
        assert utan.status_code == 422 and "hemlighet.token" in utan.json()["detail"]

        borta = await k.delete(f"/api/integrationer/{data['id']}")
        assert borta.status_code == 200
        assert (await k.delete(f"/api/integrationer/{data['id']}")).status_code == 404


@pytest.mark.anyio
async def test_ogiltig_konfig_och_saknad_hemlighet_ger_422(app):
    async with _klient(app) as k:
        fel = await k.post(
            "/api/integrationer",
            json={"typ": "http", "namn": "X", "konfig": {"requests": [{"name": "a", "url": "http://x.example.com"}]}},
        )
        assert fel.status_code == 422 and "https" in fel.json()["detail"]
        saknas = await k.post("/api/integrationer", json={"typ": "http", "namn": "Y", "konfig": ORDER})
        assert saknas.status_code == 422 and "hemlighet.token" in saknas.json()["detail"]
        mcp = await k.post(
            "/api/integrationer", json={"typ": "mcp", "namn": "Z", "konfig": {"url": "https://127.0.0.1/mcp"}}
        )
        assert mcp.status_code == 422


@pytest.mark.anyio
async def test_samma_namn_tva_ganger_ger_409(app):
    async with _klient(app) as k:
        body = {"typ": "http", "namn": "Butiken", "konfig": ORDER, "hemligheter": {"token": "sk_live_abcdef123"}}
        assert (await k.post("/api/integrationer", json=body)).status_code == 201
        assert (await k.post("/api/integrationer", json={**body, "namn": "butiken"})).status_code == 409


@pytest.mark.anyio
async def test_oklart_id_ger_404_inte_500(app):
    async with _klient(app) as k:
        assert (await k.patch("/api/integrationer/inte-ett-id", json={})).status_code == 404


@pytest.mark.anyio
async def test_provkorning_gor_riktigt_anrop_men_skrivande_kraver_tillstand(app, svara):
    mottagna = svara(lambda r: httpx.Response(200, json={"status": "skickad", "echo": r.headers.get("authorization")}))
    async with _klient(app) as k:
        skapad = (
            await k.post(
                "/api/integrationer",
                json={"typ": "http", "namn": "Butiken", "konfig": ORDER, "hemligheter": {"token": "sk_live_abcdef123"}},
            )
        ).json()
        prov = await k.post(
            f"/api/integrationer/{skapad['id']}/prova",
            json={"verktyg": "Orderstatus", "argument": {"ordernummer": "A-1"}},
        )
        assert prov.status_code == 200, prov.text
        assert "skickad" in prov.json()["resultat"]["data"]
        # Servern ekade nyckeln — provresultatet visar den inte.
        assert "sk_live_abcdef123" not in prov.text
        assert len(mottagna) == 1

        nekad = await k.post(
            f"/api/integrationer/{skapad['id']}/prova",
            json={"verktyg": "request_avboka", "argument": {"ordernummer": "A-1"}},
        )
        assert nekad.status_code == 409 and len(mottagna) == 1

        verktyg = (await k.get(f"/api/integrationer/{skapad['id']}/verktyg")).json()["verktyg"]
        assert [v["namn"] for v in verktyg] == ["request_orderstatus", "request_avboka"]
        assert [v["skrivande"] for v in verktyg] == [False, True]
