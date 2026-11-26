"""Plattformsärendena: kundens felrapporter ur Hjälprutan (migration 156).

Genom den riktiga appen med MemoryStorage, som tests/test_api.py. Hjälpens
nyckel skapas som Next-driften gör det: POST /api/keys med master-nyckeln och
sluggen `Settings.hjalp_tenant_slug`.
"""

import asyncio
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.api import plattformsarenden
from app.config import get_settings
from app.main import app

MASTER = {"X-API-Key": get_settings().snajp_master_api_key}
ANNA = str(uuid.uuid4())
BERTIL = str(uuid.uuid4())
ARBETSYTA = str(uuid.uuid4())


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _inget_mejl(monkeypatch):
    skickade: list[dict] = []

    async def falsk(**kw):
        skickade.append(kw)
        return True

    monkeypatch.setattr(plattformsarenden, "skicka_felrapport", falsk)
    return skickade


def _klient():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def hjalpnyckel(c) -> dict:
    svar = await c.post(
        "/api/keys",
        headers=MASTER,
        json={"tenant_name": "Snajp Hjälp", "slug": get_settings().hjalp_tenant_slug, "kraver_avtal": False},
    )
    assert svar.status_code == 201, svar.text
    return {"X-API-Key": svar.json()["api_key"]}


def rapport(rapportor: str = ANNA, **andra) -> dict:
    kropp = {
        "rapportor_user_id": rapportor,
        "rapportor_namn": "Anna Andersson",
        "kund_workspace_id": ARBETSYTA,
        "kund_tenant_slug": "kund-1234abcd",
        "vy": "leads",
        "roll": "owner",
        "besok_av_admin": False,
        "sida": "/dashboard/leads",
        "gjorde": "Tryckte på Kör Iris",
        "hande": "Inget hände",
        "vantade": "Att körningen skulle starta",
        "bild": None,
    }
    kropp.update(andra)
    return kropp


async def _admin_status(c, arende_id: str, status: str, **andra):
    return await c.post(
        f"/api/admin/plattformsarenden/{arende_id}/status", headers=MASTER, json={"status": status, **andra}
    )


@pytest.mark.anyio
async def test_skapa_ger_nummer_och_mottaget(_inget_mejl):
    async with app.router.lifespan_context(app), _klient() as c:
        h = await hjalpnyckel(c)
        svar = await c.post("/api/plattformsarenden", headers=h, json=rapport())
        assert svar.status_code == 201, svar.text
        kropp = svar.json()
        assert set(kropp) == {"id", "nummer", "status", "created_at"}
        assert kropp["status"] == "mottagen"
        assert kropp["nummer"].startswith("F-") and len(kropp["nummer"]) == 6
        assert not set(kropp["nummer"][2:]) & set("0O1IL2Z5S8BG6")

        await asyncio.gather(*list(plattformsarenden._pagaende))
        assert _inget_mejl == [
            {"nummer": kropp["nummer"], "arende_id": kropp["id"], "tenant_id": _inget_mejl[0]["tenant_id"]}
        ]

        lista = (await c.get(f"/api/plattformsarenden?rapportor={ANNA}", headers=h)).json()["arenden"]
        assert len(lista) == 1
        arende = lista[0]
        assert set(arende) == {
            "id", "nummer", "status", "sida", "gjorde", "created_at", "updated_at",
            "vantar_pa_kund", "testversion_url", "handelser",
        }
        assert arende["vantar_pa_kund"] is False
        assert arende["handelser"] == [
            {"tid": arende["handelser"][0]["tid"], "typ": "skapad", "status": "mottagen", "meddelande": None}
        ]


@pytest.mark.anyio
async def test_ett_mejl_som_faller_faller_inte_arendet(monkeypatch):
    async def trasig(**kw):
        raise RuntimeError("SMTP nere")

    monkeypatch.setattr(plattformsarenden, "skicka_felrapport", trasig)
    async with app.router.lifespan_context(app), _klient() as c:
        h = await hjalpnyckel(c)
        svar = await c.post("/api/plattformsarenden", headers=h, json=rapport())
        assert svar.status_code == 201
        await asyncio.gather(*list(plattformsarenden._pagaende))
        lista = (await c.get(f"/api/plattformsarenden?rapportor={ANNA}", headers=h)).json()["arenden"]
        assert [a["id"] for a in lista] == [svar.json()["id"]]


@pytest.mark.anyio
async def test_en_annan_rapportor_ser_inget():
    async with app.router.lifespan_context(app), _klient() as c:
        h = await hjalpnyckel(c)
        await c.post("/api/plattformsarenden", headers=h, json=rapport(ANNA))
        await c.post("/api/plattformsarenden", headers=h, json=rapport(BERTIL, gjorde="Bertils eget"))
        anna = (await c.get(f"/api/plattformsarenden?rapportor={ANNA}", headers=h)).json()["arenden"]
        bertil = (await c.get(f"/api/plattformsarenden?rapportor={BERTIL}", headers=h)).json()["arenden"]
        okand = (await c.get(f"/api/plattformsarenden?rapportor={uuid.uuid4()}", headers=h)).json()["arenden"]
        assert [a["gjorde"] for a in anna] == ["Tryckte på Kör Iris"]
        assert [a["gjorde"] for a in bertil] == ["Bertils eget"]
        assert okand == []
        # Ett rapportörs-id som inte är ett uuid når ingenting.
        assert (await c.get("/api/plattformsarenden?rapportor=alla", headers=h)).status_code == 422
        assert (await c.get("/api/plattformsarenden", headers=h)).status_code == 422


@pytest.mark.anyio
async def test_validering_av_sida_och_bild():
    async with app.router.lifespan_context(app), _klient() as c:
        h = await hjalpnyckel(c)
        for sida in ("https://snajp.se/dashboard", "/dashboard?lead=1", "//evil", "dashboard", "/" + "a" * 300):
            svar = await c.post("/api/plattformsarenden", headers=h, json=rapport(sida=sida))
            assert svar.status_code == 422, sida
        svar = await c.post("/api/plattformsarenden", headers=h, json=rapport(bild="data:text/html;base64,PGI+"))
        assert svar.status_code == 422
        svar = await c.post(
            "/api/plattformsarenden", headers=h, json=rapport(bild="data:image/png;base64," + "A" * 6_000_001)
        )
        assert svar.status_code == 422
        ok = await c.post("/api/plattformsarenden", headers=h, json=rapport(bild="data:image/png;base64,iVBORw0KGgo="))
        assert ok.status_code == 201
        admin = (await c.get("/api/admin/plattformsarenden", headers=MASTER)).json()["arenden"]
        assert admin[0]["har_bild"] is True
        assert "bild" not in admin[0]


PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="


@pytest.mark.anyio
async def test_admin_hamtar_bilden_per_arende_utan_cache(caplog):
    caplog.set_level("DEBUG")
    async with app.router.lifespan_context(app), _klient() as c:
        h = await hjalpnyckel(c)
        arende_id = (await c.post("/api/plattformsarenden", headers=h, json=rapport(bild=PNG))).json()["id"]
        lagring = app.state.storage
        fore = len(lagring.adminlogg)

        svar = await c.get(f"/api/admin/plattformsarenden/{arende_id}/bild", headers=MASTER)
        assert svar.status_code == 200, svar.text
        assert svar.json() == {"bild": PNG}
        assert svar.headers["cache-control"] == "no-store"
        assert svar.headers["x-content-type-options"] == "nosniff"

        # En rad i åtkomstloggen med ärendet som resurs och inget av innehållet.
        nya = lagring.adminlogg[fore:]
        assert len(nya) == 1
        assert nya[0]["metod"] == "GET" and nya[0]["entity_id"] == arende_id
        assert nya[0]["resurs"] == "/api/admin/plattformsarenden/{arende_id}/bild"
        assert PNG[30:] not in repr(nya[0])
        # Bilden hamnar inte i någon logg.
        assert PNG[30:] not in caplog.text

        # Listan bär fortfarande bara att bilden finns.
        lista = (await c.get("/api/admin/plattformsarenden", headers=MASTER)).json()["arenden"]
        assert lista[0]["har_bild"] is True and "bild" not in lista[0]
        assert PNG[30:] not in (await c.get("/api/admin/plattformsarenden", headers=MASTER)).text


@pytest.mark.anyio
async def test_ingen_bild_okant_arende_och_fel_typ():
    async with app.router.lifespan_context(app), _klient() as c:
        h = await hjalpnyckel(c)
        utan = (await c.post("/api/plattformsarenden", headers=h, json=rapport())).json()["id"]
        svar = await c.get(f"/api/admin/plattformsarenden/{utan}/bild", headers=MASTER)
        assert svar.status_code == 404
        assert svar.headers["cache-control"] == "no-store"
        assert svar.headers["x-content-type-options"] == "nosniff"

        assert (await c.get(f"/api/admin/plattformsarenden/{uuid.uuid4()}/bild", headers=MASTER)).status_code == 404
        assert (await c.get("/api/admin/plattformsarenden/inte-ett-uuid/bild", headers=MASTER)).status_code == 404

        # Inlämningen tar bara emot PNG, JPEG, WebP och GIF: en SVG (som kan
        # bära skript) och en bild som inte är base64 lagras aldrig.
        svg = "data:image/svg+xml;base64,PHN2ZyBvbmxvYWQ9YWxlcnQoMSk+"
        for vagrad in (svg, "data:image/png;utf8,<svg onload=alert(1)>", "data:image/bmp;base64,Qk0="):
            nej = await c.post("/api/plattformsarenden", headers=h, json=rapport(bild=vagrad))
            assert nej.status_code == 422, vagrad
        for godtagen in ("png", "jpeg", "webp", "gif"):
            ja = await c.post("/api/plattformsarenden", headers=h, json=rapport(bild=f"data:image/{godtagen};base64,iVBO"))
            assert ja.status_code == 201, godtagen

        # En SVG som ändå står i en rad (skriven förbi inlämningen) lämnas aldrig ut.
        med_svg = (await c.post("/api/plattformsarenden", headers=h, json=rapport(bild=PNG))).json()["id"]
        app.state.storage._plattformsarenden()[med_svg]["bild"] = svg
        svar = await c.get(f"/api/admin/plattformsarenden/{med_svg}/bild", headers=MASTER)
        assert svar.status_code == 415
        assert "PHN2Zy" not in svar.text
        assert svar.headers["x-content-type-options"] == "nosniff"

        # Rätt typ men inte base64 (en rad skriven förbi inlämningen).
        trasig = (await c.post("/api/plattformsarenden", headers=h, json=rapport(bild="data:image/png;base64,iVBO"))).json()["id"]
        app.state.storage._plattformsarenden()[trasig]["bild"] = "data:image/png;utf8,<svg onload=alert(1)>"
        assert (await c.get(f"/api/admin/plattformsarenden/{trasig}/bild", headers=MASTER)).status_code == 415


@pytest.mark.anyio
async def test_en_kundnyckel_far_aldrig_lasa_bilden():
    async with app.router.lifespan_context(app), _klient() as c:
        h = await hjalpnyckel(c)
        arende_id = (await c.post("/api/plattformsarenden", headers=h, json=rapport(bild=PNG))).json()["id"]
        kund = await c.post(
            "/api/keys", headers=MASTER, json={"tenant_name": "Kund AB", "slug": "kund-bildtest", "kraver_avtal": False}
        )
        assert kund.status_code == 201, kund.text
        kundnyckel = {"X-API-Key": kund.json()["api_key"]}

        # Alla plattformsadmin ser alla ärenden, men ingen kundnyckel (inte
        # heller hjälpens egen, som skapade ärendet) når adminvägen.
        for huvud in (h, kundnyckel, {"X-API-Key": "fel-nyckel"}, {}):
            svar = await c.get(f"/api/admin/plattformsarenden/{arende_id}/bild", headers=huvud)
            assert svar.status_code in (401, 403), (huvud, svar.status_code)
            assert "iVBOR" not in svar.text
        # Kundens egen väg har ingen bildläsning alls.
        assert (await c.get(f"/api/plattformsarenden/{arende_id}/bild", headers=h)).status_code in (404, 405)


@pytest.mark.anyio
async def test_svar_bara_nar_snajp_behover_mer():
    async with app.router.lifespan_context(app), _klient() as c:
        h = await hjalpnyckel(c)
        arende_id = (await c.post("/api/plattformsarenden", headers=h, json=rapport())).json()["id"]

        # Fel läge: mottagen.
        fel = await c.post(
            f"/api/plattformsarenden/{arende_id}/svar", headers=h, json={"rapportor_user_id": ANNA, "text": "Hej"}
        )
        assert fel.status_code == 409

        # behover_mer kräver ett meddelande till kunden.
        assert (await _admin_status(c, arende_id, "behover_mer")).status_code == 422
        andrad = await _admin_status(c, arende_id, "behover_mer", meddelande_till_kund="Vilken webbläsare?")
        assert andrad.status_code == 200, andrad.text

        lista = (await c.get(f"/api/plattformsarenden?rapportor={ANNA}", headers=h)).json()["arenden"]
        assert lista[0]["status"] == "behover_mer" and lista[0]["vantar_pa_kund"] is True
        assert lista[0]["handelser"][-1]["meddelande"] == "Vilken webbläsare?"

        # En annan rapportör: ärendet finns inte för honom.
        annan = await c.post(
            f"/api/plattformsarenden/{arende_id}/svar", headers=h, json={"rapportor_user_id": BERTIL, "text": "Jag"}
        )
        assert annan.status_code == 404
        okant = await c.post(
            f"/api/plattformsarenden/{uuid.uuid4()}/svar", headers=h, json={"rapportor_user_id": ANNA, "text": "x"}
        )
        assert okant.status_code == 404

        svar = await c.post(
            f"/api/plattformsarenden/{arende_id}/svar", headers=h, json={"rapportor_user_id": ANNA, "text": "Firefox"}
        )
        assert svar.status_code == 200, svar.text
        assert svar.json()["status"] == "undersoks"
        assert svar.json()["vantar_pa_kund"] is False
        assert svar.json()["handelser"][-1] == {
            "tid": svar.json()["handelser"][-1]["tid"], "typ": "kundsvar", "status": "undersoks", "meddelande": "Firefox",
        }
        # Andra gången står ärendet inte längre i läget.
        igen = await c.post(
            f"/api/plattformsarenden/{arende_id}/svar", headers=h, json={"rapportor_user_id": ANNA, "text": "Igen"}
        )
        assert igen.status_code == 409


@pytest.mark.anyio
async def test_utslag_ja_och_nej():
    async with app.router.lifespan_context(app), _klient() as c:
        h = await hjalpnyckel(c)
        ett = (await c.post("/api/plattformsarenden", headers=h, json=rapport())).json()["id"]
        tva = (await c.post("/api/plattformsarenden", headers=h, json=rapport())).json()["id"]

        fel = await c.post(
            f"/api/plattformsarenden/{ett}/utslag", headers=h, json={"rapportor_user_id": ANNA, "fungerar": True}
        )
        assert fel.status_code == 409

        for arende_id in (ett, tva):
            svar = await _admin_status(
                c, arende_id, "redo_att_testa", testversion_url="https://forhand.example.test/x"
            )
            assert svar.json()["testversion_url"] == "https://forhand.example.test/x"
        assert (await _admin_status(c, ett, "redo_att_testa", testversion_url="http://osaker")).status_code == 422

        lista = (await c.get(f"/api/plattformsarenden?rapportor={ANNA}", headers=h)).json()["arenden"]
        assert all(a["vantar_pa_kund"] and a["status"] == "redo_att_testa" for a in lista)

        ja = await c.post(
            f"/api/plattformsarenden/{ett}/utslag", headers=h, json={"rapportor_user_id": ANNA, "fungerar": True}
        )
        assert ja.status_code == 200 and ja.json()["status"] == "kund_godkand"

        nej = await c.post(
            f"/api/plattformsarenden/{tva}/utslag",
            headers=h,
            json={"rapportor_user_id": ANNA, "fungerar": False, "kommentar": "Knappen är fortfarande grå"},
        )
        assert nej.status_code == 200
        assert nej.json()["status"] == "rattning_pagar"
        assert nej.json()["handelser"][-1]["typ"] == "utslag"
        assert nej.json()["handelser"][-1]["meddelande"] == "Knappen är fortfarande grå"

        annan = await c.post(
            f"/api/plattformsarenden/{tva}/utslag", headers=h, json={"rapportor_user_id": BERTIL, "fungerar": True}
        )
        assert annan.status_code == 404


@pytest.mark.anyio
async def test_adminvyn_ser_allt_kunden_bara_det_synliga():
    async with app.router.lifespan_context(app), _klient() as c:
        h = await hjalpnyckel(c)
        arende_id = (await c.post("/api/plattformsarenden", headers=h, json=rapport(besok_av_admin=True))).json()["id"]

        assert (await _admin_status(c, arende_id, "stangd")).status_code == 422
        assert (await _admin_status(c, arende_id, "okand")).status_code == 422
        assert (await _admin_status(c, str(uuid.uuid4()), "undersoks")).status_code == 404

        await _admin_status(c, arende_id, "undersoks")
        await _admin_status(c, arende_id, "redo_att_testa", testversion_url="https://forhand.example.test/x")
        andrad = await _admin_status(c, arende_id, "i_main", meddelande_till_kund="Rättat i Snajp.")
        admin = andrad.json()
        assert admin["status"] == "i_main"
        assert admin["testversion_url"] is None  # testversionen är borttagen
        assert admin["besok_av_admin"] is True
        assert admin["rapportor_user_id"] == ANNA and admin["kund_workspace_id"] == ARBETSYTA
        assert admin["hande"] == "Inget hände" and admin["vantade"] == "Att körningen skulle starta"
        assert [h["typ"] for h in admin["handelser"]] == ["skapad", "status", "status", "status"]
        assert all({"synlig_for_kund", "aktor"} <= set(h) for h in admin["handelser"])
        assert admin["handelser"][-1]["aktor"] == "plattformsadmin"

        # Statusfiltret.
        assert len((await c.get("/api/admin/plattformsarenden?status=i_main", headers=MASTER)).json()["arenden"]) == 1
        assert (await c.get("/api/admin/plattformsarenden?status=mottagen", headers=MASTER)).json()["arenden"] == []

        kund = (await c.get(f"/api/plattformsarenden?rapportor={ANNA}", headers=h)).json()["arenden"][0]
        assert kund["status"] == "i_main" and kund["vantar_pa_kund"] is False
        assert kund["handelser"][-1]["meddelande"] == "Rättat i Snajp."
        assert all(set(h) == {"tid", "typ", "status", "meddelande"} for h in kund["handelser"])
        assert "hande" not in kund and "rapportor_namn" not in kund
