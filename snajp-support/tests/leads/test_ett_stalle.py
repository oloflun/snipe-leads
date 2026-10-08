"""Ett bolag, ett ställe (Antons krav 2026-10-08).

create_prospect returnerar det befintliga prospektet för samma bolag
(org.nr, annars namnet utan bolagsform), en listrad som blivit prospekt döljs
i listan, och "Pröva mot Iris igen" skapar aldrig ett bolag två gånger hur
många gånger den än körs."""

from __future__ import annotations

import pytest

from app.api import leads as leads_api
from app.leads import omprova
from app.storage.memory import MemoryStorage

T = "00000000-0000-4000-a000-000000000001"

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def test_samma_bolag_blir_ett_prospekt():
    s = MemoryStorage()
    a = await s.create_prospect(T, company_name="Alfa Bygg AB", origin="iris", profil={"orgnr": "556000-0001"})
    b = await s.create_prospect(T, company_name="ALFA BYGG", origin="ring")
    c = await s.create_prospect(T, company_name="Annat namn AB", origin="iris", profil={"orgnr": "5560000001"})
    assert b["id"] == a["id"] and b["fanns_redan"]
    assert c["id"] == a["id"]
    assert len(await s.list_prospects(T)) == 1


async def test_samma_namn_men_olika_orgnr_ar_tva_bolag():
    s = MemoryStorage()
    await s.create_prospect(T, company_name="Bygg AB", origin="iris", profil={"orgnr": "556000-0001"})
    await s.create_prospect(T, company_name="Bygg AB", origin="iris", profil={"orgnr": "556000-0002"})
    assert len(await s.list_prospects(T)) == 2


async def test_testprospekt_paverkas_inte():
    s = MemoryStorage()
    await s.create_prospect(T, company_name="Alfa Bygg AB", origin="iris")
    t = await s.create_prospect(T, company_name="Alfa Bygg AB", origin="test")
    assert not t.get("fanns_redan")


async def test_flyttad_listrad_doljs_men_raderas_inte():
    s = MemoryStorage()
    lista = await s.create_lead_list(T, titel="L", icp={}, antal=2)
    rad = await s.add_lead_list_item(T, list_id=lista["id"], item_typ="bolag", company_name="Alfa Bygg AB", signal="listspar")
    await s.markera_listrad_flyttad(T, rad["id"], signal_detalj="x → flyttad till Iris 2026-10-08")
    assert await s.list_lead_list_items(T, lista["id"]) == []
    assert len(s.lead_list_items) == 1
    [l] = await s.list_lead_lists(T)
    assert l["item_count"] == 0


async def test_processa_om_berikar_raderna_och_flyttar_inget(monkeypatch):
    async def inget_register(rad):
        return None

    async def sok_alla(par, **_):
        svar = []
        for rad, _bolag in par:
            alfa = rad["company_name"].startswith("Alfa")
            k = {"company_name": rad["company_name"], "website": "https://alfabygg.se", "vd_namn": "Eva VD",
                 "orgnr": "556000-0001" if alfa else "556000-0002"}
            svar.append((k, {"contact_email": "info@alfabygg.se"} if alfa else {"contact_phone": "031-12 34 56"}))
        return svar

    monkeypatch.setattr(omprova, "hamta_bolag", inget_register)
    monkeypatch.setattr(omprova, "sok_alla", sok_alla)
    monkeypatch.setattr(leads_api.sidhamtning, "starta", lambda *a, **k: None)

    s = MemoryStorage()
    lista = await s.create_lead_list(T, titel="Utan webbplats", icp={}, antal=2)
    for namn in ("Alfa Bygg AB", "Beta Rör AB"):
        await s.add_lead_list_item(T, list_id=lista["id"], item_typ="bolag", company_name=namn, signal="listspar")
    app_state = type("S", (), {"storage": s})()
    rader = await s.list_lead_list_items(T, lista["id"])
    assert await leads_api._omprova_bakgrund(app_state, T, rader) == {"iris": 1, "ring": 1}
    alfa, beta = await s.list_lead_list_items(T, lista["id"])
    assert (alfa["contact_email"], alfa["website"]) == ("info@alfabygg.se", "https://alfabygg.se")
    assert alfa["signal_detalj"].startswith("Mejladress hittad")
    assert (beta["contact_phone"], beta["contact_name"]) == ("031-12 34 56", "Eva VD")
    assert await s.list_prospects(T) == [], "Processa om flyttar inget själv"


def test_bolag_som_avvecklas_blir_aldrig_lead():
    rad = {"company_name": "Slut AB", "signal_detalj": "x"}
    kandidat = {"company_name": "Slut AB", "avvecklas": True, "_epost": "info@slut.se"}
    assert omprova.planera(rad, kandidat, {"contact_email": "info@slut.se"}) == (
        "ej_kvalificerad", "bolaget avvecklas", None)
