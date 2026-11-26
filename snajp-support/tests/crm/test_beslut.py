"""Antons svar 2026-11-26 som kod (docs/BESLUT.md samma dag).

- Tidigare kunder är fria att bearbeta.
- Ett CRM-bolag med organisationsnummer utesluter på numret, inte på namnet.
- Privatpersoner hoppas över om anslutningen inte slår på dem, och är aldrig
  kontaktbara när de sparas.
- CRM:et är ett tillägg, fritt under provperioden.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.crm import lagring, tillgang
from app.leads import upptagna

from .conftest import ORGNR_A, ORGNR_B

V1 = "/api/crm/v1"
pytestmark = pytest.mark.anyio


# -- Upptagna bolag ----------------------------------------------------------


async def test_tidigare_kund_ar_fri_men_inte_om_posten_sager_kontakta_inte(buddy, storage):
    async with buddy.klient() as k:
        fri = (await k.post(f"{V1}/companies", json={
            "name": "Gamla Kunden AB", "org_number": ORGNR_A, "relation": "former_customer"})).json()
        await k.post(f"{V1}/companies", json={
            "name": "Vill Inte AB", "org_number": ORGNR_B, "relation": "former_customer", "do_not_contact": True})
        sedda = await upptagna.hamta(storage, buddy.id)
        assert not upptagna.upptagen(sedda, "Gamla Kunden AB", ORGNR_A)
        assert upptagna.upptagen(sedda, "Vill Inte AB", ORGNR_B)
        # Blir den kund igen är den upptagen igen.
        await k.patch(f"{V1}/companies/{fri['id']}", json={"relation": "customer"})
        assert upptagna.upptagen(await upptagna.hamta(storage, buddy.id), "Annat Namn AB", ORGNR_A)


async def test_bolag_med_nummer_utesluter_pa_numret_inte_pa_namnet(buddy, storage):
    async with buddy.klient() as k:
        await k.post(f"{V1}/companies", json={"name": "Bygg AB", "org_number": ORGNR_A})
        await k.post(f"{V1}/companies", json={"name": "Utan Nummer AB"})
        sedda = await upptagna.hamta(storage, buddy.id)
        # Ett annat bolag som råkar heta likadant är inte kundens kund.
        assert not upptagna.upptagen(sedda, "Bygg AB", ORGNR_B)
        # Samma nummer under ett annat namn är det.
        assert upptagna.upptagen(sedda, "Bygg i Umeå AB", ORGNR_A)
        # En kandidat utan nummer har bara namnet att jämföra med.
        assert upptagna.upptagen(sedda, "bygg")
        # Bolaget utan nummer utesluter på namnet som förut.
        assert upptagna.upptagen(sedda, "Utan Nummer", ORGNR_B)


def test_nyckelmangden_overlever_normaliseringen():
    """`upptagna.nycklar` körs på mängden i sökningen: märkta nycklar ska stå kvar."""
    sedda = upptagna.bolagsnycklar([{"company_name": "Bygg AB", "orgnr": ORGNR_A, "bara_orgnr": True}])
    assert upptagna.nycklar(sedda) == sedda
    assert not upptagna.upptagen(upptagna.nycklar(sedda), "Bygg AB", ORGNR_B)


# -- Privatpersoner ----------------------------------------------------------


def _fortnox(nr: str, namn: str, typ: str, **mer) -> dict:
    return {"CustomerNumber": nr, "Name": namn, "Type": typ, "Active": True, **mer}


async def test_privatpersoner_hoppas_over_som_standard(buddy):
    async with buddy.klient() as k:
        assert (await k.post(f"{V1}/connections", json={"name": "fortnox", "system": "fortnox"})).status_code == 201
        ut = (await k.post(f"{V1}/sync/companies", json={"connection": "fortnox", "items": [
            _fortnox("1", "Bolaget AB", "COMPANY", OrganisationNumber=ORGNR_A),
            _fortnox("2", "Anna Berg", "PRIVATE", OrganisationNumber="19850101-2384", Email="anna@example.se"),
        ]})).json()
        assert [p["status"] for p in ut["items"]] == ["created", "skipped"]
        assert ut["items"][1]["reason"] == "privatperson"
        assert len((await k.get(f"{V1}/companies")).json()["data"]) == 1
        # Felloggen bär inget av personens uppgifter.
        assert "1985" not in str(ut["run"]["errors"]) and "anna@" not in str(ut["run"]["errors"])


async def test_paslagna_privatpersoner_sparas_markta_och_aldrig_kontaktbara(buddy, storage):
    async with buddy.klient() as k:
        anslutning = (await k.post(f"{V1}/connections", json={
            "name": "fortnox", "system": "fortnox", "include_private_persons": True})).json()
        assert anslutning["include_private_persons"] is True
        ut = (await k.post(f"{V1}/sync/companies", json={"connection": "fortnox", "items": [
            _fortnox("2", "Anna Berg", "PRIVATE", OrganisationNumber="19850101-2384", Email="anna@example.se"),
        ]})).json()
        assert ut["items"][0]["status"] == "created" and "field_errors" not in ut["items"][0]
        post = (await k.get(f"{V1}/companies/{ut['items'][0]['id']}")).json()
        assert post["private_person"] is True and post["do_not_contact"] is True
        assert post["org_number"] is None and post["sole_proprietor"] is False
        # Går inte att göra kontaktbar, vare sig för hand eller av en ny synk.
        andrad = (await k.patch(f"{V1}/companies/{post['id']}", json={"do_not_contact": False})).json()
        assert andrad["do_not_contact"] is True
        # Adressen ligger bland dem som aldrig får ett utskick.
        assert "anna@example.se" in await lagring.kontakta_inte_adresser(storage, buddy.id)
        rad = await lagring.hamta_post(storage, buddy.id, "bolag", post["id"])
        assert not lagring.far_bearbetas(rad)


async def test_privatperson_for_hand_blir_aldrig_kontaktbar(buddy):
    async with buddy.klient() as k:
        post = (await k.post(f"{V1}/companies", json={"name": "Karl Ek", "private_person": True,
                                                      "do_not_contact": False})).json()
        assert post["private_person"] is True and post["do_not_contact"] is True


async def test_kontakta_inte_pa_bolaget_galler_ocksa_dess_personer(buddy, annan, storage):
    async with buddy.klient() as k:
        bolag = (await k.post(f"{V1}/companies", json={"name": "Tyst AB", "email": "info@tyst.se",
                                                       "do_not_contact": True})).json()
        await k.post(f"{V1}/people", json={"email": "vd@tyst.se", "company_id": bolag["id"]})
        await k.post(f"{V1}/people", json={"email": "fri@annat.se"})
        await k.post(f"{V1}/people", json={"email": "nej@annat.se", "do_not_contact": True})
    assert await lagring.kontakta_inte_adresser(storage, buddy.id) == {"info@tyst.se", "vd@tyst.se", "nej@annat.se"}
    assert await lagring.kontakta_inte_adresser(storage, annan.id) == set()


# -- Tillägget ---------------------------------------------------------------


def test_regeln_for_tillgang():
    idag = date(2026, 11, 26)
    assert tillgang.avgor(None, idag)                                    # ingen arbetsyta
    assert tillgang.avgor({"addons": ["crm"], "trial_slut": None}, idag)  # tillägget
    assert tillgang.avgor({"addons": [], "trial_slut": idag}, idag)       # sista provdagen
    assert tillgang.avgor({"addons": [], "trial_slut": "2026-12-01"}, idag)
    assert not tillgang.avgor({"addons": ["leadlists"], "trial_slut": idag - timedelta(days=1)}, idag)
    assert not tillgang.avgor({"addons": [], "trial_slut": None}, idag)


async def test_utan_tillagg_och_efter_provperioden_ar_crm_stangt(buddy, annan, storage):
    storage._crm_tillgang = {buddy.id: {"addons": [], "trial_slut": date(2020, 1, 1)}}
    async with buddy.klient() as k:
        for metod, vag in [("get", f"{V1}/me"), ("get", f"{V1}/companies"), ("post", f"{V1}/companies")]:
            svar = await getattr(k, metod)(vag, **({"json": {"name": "X AB"}} if metod == "post" else {}))
            assert svar.status_code == 403 and svar.json()["detail"]["code"] == "addon_missing", vag
    # Den interna ytan med kundens egen nyckel: samma grind.
    await storage.create_api_key(buddy.id, tenant_name="Buddy", raw_key="snajp_live_appens_egen_nyckel")
    async with buddy.klient("snajp_live_appens_egen_nyckel") as k:
        for vag in ("/api/crm/oversikt", "/api/crm/nycklar"):
            svar = await k.get(vag)
            assert svar.status_code == 403 and svar.json()["detail"]["code"] == "addon_missing", vag
    # Den andra kunden påverkas inte.
    async with annan.klient() as k:
        assert (await k.get(f"{V1}/companies")).status_code == 200
    # Tillägget öppnar, och provperioden gör det också.
    for grund in ({"addons": ["crm"], "trial_slut": None},
                  {"addons": [], "trial_slut": date.today() + timedelta(days=3)}):
        storage._crm_tillgang[buddy.id] = grund
        tillgang.nollstall()
        async with buddy.klient() as k:
            assert (await k.get(f"{V1}/companies")).status_code == 200
