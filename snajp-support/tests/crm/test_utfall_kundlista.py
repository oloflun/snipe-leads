"""Utfall som gäller åt båda håll, och den samlade kundlistan
(app/crm/utfall.py, app/crm/kundlista.py).
"""

from __future__ import annotations

import pytest

from app.api import crm_v1, crm_v1_tidslinje
from app.crm import lagring

from .conftest import ORGNR_A, ORGNR_B, ORGNR_C

V1 = "/api/crm/v1"
pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
def _vagar(app):
    """Kopplas här tills `crm_v1.py` inkluderar routern själv."""
    if not any(getattr(r, "path", "").endswith("/timeline") for r in app.routes):
        app.include_router(crm_v1_tidslinje.koppla(crm_v1), prefix=V1)


async def _lead(storage, tenant_id: str, namn: str, orgnr: str, epost: str, *, status: str | None = None) -> dict:
    p = await storage.create_prospect(tenant_id, company_name=namn, contact_email=epost)
    await storage.update_prospect(tenant_id, p["id"], orgnr=orgnr, **({"status": status} if status else {}))
    return p


async def _ko(storage, tenant_id: str, lead: dict) -> None:
    """Ett utskick som väntar på att gå."""
    trad = await storage.ensure_outreach_thread(tenant_id, prospect_id=lead["id"])
    await storage.queue_outreach_message(tenant_id, thread_id=trad["id"], body="Hej", subject="Förslag",
                                         humanizer_variant="a", scheduled_at="2030-01-01T09:00:00+00:00")


async def _vantande(storage, tenant_id: str) -> int:
    return len([i for i in storage.send_queue.get(tenant_id, []) if i["status"] == "queued"])


# -- Från CRM:et till leadsflödet --------------------------------------------


async def test_kontakta_inte_i_crm_stoppar_leadet_och_sparrar_adressen(buddy, annan, storage):
    async with buddy.klient() as k:
        bolag = (await k.post(f"{V1}/companies", json={"name": "Bygg AB", "org_number": ORGNR_A})).json()
    lead = await _lead(storage, buddy.id, "Byggarna AB", ORGNR_A, "vd@bygg.se", status="contacted")
    orort = await _lead(storage, buddy.id, "Annat AB", ORGNR_B, "vd@annat.se", status="contacted")
    await _ko(storage, buddy.id, lead)
    await _ko(storage, buddy.id, orort)
    assert await _vantande(storage, buddy.id) == 2

    async with buddy.klient() as k:
        svar = await k.post(f"{V1}/companies/{bolag['id']}/outcome", json={"outcome": "do_not_contact",
                                                                          "note": "Bad oss sluta höra av oss."})
        assert svar.status_code == 200, svar.text
        assert svar.json()["lead_ids"] == [lead["id"]] and svar.json()["company"]["do_not_contact"] is True
    # Leadet är avslutat, adressen spärrad och det som väntade är stoppat. Det andra leadet är orört.
    assert (await storage.get_prospect(buddy.id, lead["id"]))["status"] == "suppressed"
    assert "vd@bygg.se" in await storage.list_suppressions(buddy.id)
    assert await _vantande(storage, buddy.id) == 1
    assert (await storage.get_prospect(buddy.id, orort["id"]))["status"] == "contacted"
    # Samtalet står i leadets samtalslogg och på bolagets tidslinje.
    (samtal,) = await storage.list_lead_samtal(buddy.id, prospect_id=lead["id"])
    assert samtal["utfall"] == "kontakta_inte" and samtal["anteckning"] == "Bad oss sluta höra av oss."
    async with buddy.klient() as k:
        typer = [p["type"] for p in (await k.get(f"{V1}/companies/{bolag['id']}/timeline")).json()["data"]]
        assert "call" in typer and "record_updated" in typer
    # Den andra kunden kan inte sätta utfall på bolaget.
    async with annan.klient() as k:
        assert (await k.post(f"{V1}/companies/{bolag['id']}/outcome", json={"outcome": "won"})).status_code == 404


async def test_vunnen_gor_bolaget_till_kund_och_stoppar_utskicken(buddy, storage):
    async with buddy.klient() as k:
        bolag = (await k.post(f"{V1}/companies", json={"name": "Bygg AB", "org_number": ORGNR_A,
                                                       "relation": "prospect"})).json()
    lead = await _lead(storage, buddy.id, "Bygg AB", ORGNR_A, "vd@bygg.se", status="meeting")
    await _ko(storage, buddy.id, lead)
    async with buddy.klient() as k:
        svar = (await k.post(f"{V1}/companies/{bolag['id']}/outcome", json={"outcome": "won"})).json()
        assert svar["company"]["relation"] == "customer" and svar["company"]["customer_since"]
        # En gång till ändrar ingenting och skriver ingen ny status.
        await k.post(f"{V1}/companies/{bolag['id']}/outcome", json={"outcome": "won"})
    assert (await storage.get_prospect(buddy.id, lead["id"]))["status"] == "won"
    assert await _vantande(storage, buddy.id) == 0
    assert len([r for r in await storage.list_status_logg(buddy.id, prospect_id=lead["id"]) if r["till"] == "won"]) == 1


async def test_aterkom_kraver_datum_och_ett_bolag_utan_lead_far_bara_sin_egen_andring(buddy, storage):
    async with buddy.klient() as k:
        bolag = (await k.post(f"{V1}/companies", json={"name": "Utan Lead AB", "org_number": ORGNR_A})).json()
        svar = await k.post(f"{V1}/companies/{bolag['id']}/outcome", json={"outcome": "call_back"})
        assert svar.status_code == 422 and svar.json()["detail"]["code"] == "call_back_date_required"
        ok = await k.post(f"{V1}/companies/{bolag['id']}/outcome", json={"outcome": "call_back",
                                                                        "call_back_on": "2026-12-15"})
        assert ok.status_code == 200 and ok.json()["lead_ids"] == []
        tyst = (await k.post(f"{V1}/companies/{bolag['id']}/outcome", json={"outcome": "do_not_contact"})).json()
        assert tyst["lead_ids"] == [] and tyst["company"]["do_not_contact"] is True
        assert (await k.post(f"{V1}/companies/{bolag['id']}/outcome", json={"outcome": "sold"})).status_code == 422
    # Med lead: återkom sparas som samtal med datumet, och leadet står kvar.
    lead = await _lead(storage, buddy.id, "Med Lead AB", ORGNR_B, "vd@medlead.se", status="contacted")
    async with buddy.klient() as k:
        med = (await k.post(f"{V1}/companies", json={"name": "Med Lead AB", "org_number": ORGNR_B})).json()
        await k.post(f"{V1}/companies/{med['id']}/outcome", json={"outcome": "call_back", "call_back_on": "2026-12-15"})
    (samtal,) = await storage.list_lead_samtal(buddy.id, prospect_id=lead["id"])
    assert samtal["utfall"] == "aterkom" and str(samtal["aterkom_datum"]).startswith("2026-12-15")
    assert (await storage.get_prospect(buddy.id, lead["id"]))["status"] == "contacted"
    # Bara läsning räcker inte för att sätta utfall.
    las = await buddy.ny_nyckel(["crm:las"])
    async with buddy.klient(las) as k:
        assert (await k.post(f"{V1}/companies/{med['id']}/outcome", json={"outcome": "won"})).status_code == 403


# -- Från leadsflödet till CRM:et --------------------------------------------


async def test_leadets_avslutande_utfall_galler_bolaget_i_crm(buddy, annan, storage):
    async with buddy.klient() as k:
        bolag = (await k.post(f"{V1}/companies", json={"name": "Bygg AB", "org_number": ORGNR_A})).json()
        utan = (await k.post(f"{V1}/companies", json={"name": "Utan Lead AB", "org_number": ORGNR_C})).json()
        assert (await k.get(f"{V1}/companies/{utan['id']}/iris")).json() == {
            "leads": [], "outcome": None, "do_not_contact": False}
    lead = await _lead(storage, buddy.id, "Bygg AB", ORGNR_A, "vd@bygg.se", status="contacted")
    async with buddy.klient() as k:
        lage = (await k.get(f"{V1}/companies/{bolag['id']}/iris")).json()
        assert lage["leads"] == [{"id": lead["id"], "name": "Bygg AB", "status": "contacted",
                                  "created_at": lage["leads"][0]["created_at"]}]
        assert lage["outcome"] is None and lage["do_not_contact"] is False
        # Leadet ber att slippa kontakt, i leadsflödet. Posten i CRM:et säger fortfarande ingenting själv.
        await storage.update_prospect(buddy.id, lead["id"], status="suppressed")
        lage = (await k.get(f"{V1}/companies/{bolag['id']}/iris")).json()
        assert lage["outcome"] == "do_not_contact" and lage["do_not_contact"] is True
        assert (await k.get(f"{V1}/companies/{bolag['id']}")).json()["do_not_contact"] in (False, None)
    async with annan.klient() as k:
        assert (await k.get(f"{V1}/companies/{bolag['id']}/iris")).status_code == 404


# -- Den samlade kundlistan --------------------------------------------------


async def test_kundlistan_delar_pa_egna_och_iris_och_visar_ett_bolag_en_gang(buddy, annan, storage):
    async with buddy.klient() as k:
        egen = (await k.post(f"{V1}/companies", json={"name": "Egen Kund AB", "org_number": ORGNR_A,
                                                      "customer_since": "2024-03-01"})).json()
        await k.post(f"{V1}/companies", json={"name": "Bara Prospekt AB", "relation": "prospect"})
        await k.post(f"{V1}/companies", json={"name": "Tidigare AB", "relation": "former_customer"})
    # Ett vunnet lead som redan är egen kund, ett som bara finns hos Iris, och ett som inte är vunnet.
    samma = await _lead(storage, buddy.id, "Egen Kund Aktiebolag", ORGNR_A, "vd@egen.se", status="won")
    iris = await _lead(storage, buddy.id, "Iris Vann AB", ORGNR_B, "vd@irisvann.se", status="won")
    await _lead(storage, buddy.id, "Inte Vunnen AB", ORGNR_C, "vd@inte.se", status="meeting")

    async with buddy.klient() as k:
        alla = (await k.get(f"{V1}/customers")).json()
        assert alla["counts"] == {"own": 1, "iris": 1}
        assert [(r["origin"], r["name"]) for r in alla["data"]] == [("own", "Egen Kund AB"), ("iris", "Iris Vann AB")]
        egna, vunna = alla["data"]
        assert egna == {"origin": "own", "company_id": egen["id"], "lead_id": samma["id"], "name": "Egen Kund AB",
                        "org_number": ORGNR_A, "customer_since": "2024-03-01", "private_person": False}
        assert vunna["company_id"] is None and vunna["lead_id"] == iris["id"] and vunna["org_number"] == ORGNR_B
        assert [r["origin"] for r in (await k.get(f"{V1}/customers", params={"origin": "iris"})).json()["data"]] == ["iris"]
        assert [r["name"] for r in (await k.get(f"{V1}/customers", params={"q": "vann"})).json()["data"]] == ["Iris Vann AB"]
        # Räknarna gäller hela listan, också när den är filtrerad.
        assert (await k.get(f"{V1}/customers", params={"origin": "own"})).json()["counts"] == {"own": 1, "iris": 1}
    # Det vunna leadet har inte blivit ett bolag i CRM:et.
    assert await lagring.hitta_poster(storage, buddy.id, "bolag", "orgnr_nyckel", ["5560160680"]) == []
    async with annan.klient() as k:
        assert (await k.get(f"{V1}/customers")).json() == {"data": [], "counts": {"own": 0, "iris": 0}}
