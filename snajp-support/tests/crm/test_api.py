"""/api/crm/v1 från början till slut: nycklar och omfång, tenantisolering,
bolag och personer, synken med konfliktregler, idempotens och taket.
"""

from __future__ import annotations

import pytest

from app.api import crm_v1
from app.crm import lagring
from app.leads import upptagna

from .conftest import ORGNR_A, ORGNR_B, ORGNR_C

V1 = "/api/crm/v1"
pytestmark = pytest.mark.anyio


def hubspot(eid: str, namn: str, orgnr: str | None = None, **egenskaper) -> dict:
    return {"id": eid, "updatedAt": egenskaper.pop("updatedAt", "2026-11-20T08:00:00.000Z"),
            "archived": egenskaper.pop("archived", False),
            "properties": {"name": namn, **({"orgnr": orgnr} if orgnr else {}), "lifecyclestage": "customer", **egenskaper}}


async def _anslutning(k, namn="hubspot", **falt) -> dict:
    svar = await k.post(f"{V1}/connections", json={"name": namn, "system": "hubspot", **falt})
    assert svar.status_code == 201, svar.text
    return svar.json()


# -- Nycklar och omfång ------------------------------------------------------


async def test_utan_nyckel_och_med_fel_nyckel(buddy):
    async with buddy.klient("") as k:
        assert (await k.get(f"{V1}/companies")).status_code == 401
    async with buddy.klient("snajp_crm_finns_inte") as k:
        assert (await k.get(f"{V1}/companies")).status_code == 401


async def test_crm_nyckel_nar_inget_annat_an_crm_apit(buddy):
    """Kärnan i omfången: nyckeln Buddy lägger i sitt CRM når inte resten."""
    async with buddy.klient() as k:
        assert (await k.get(f"{V1}/me")).status_code == 200
        svar = await k.get("/api/integrationer")
        assert svar.status_code == 403
        assert "/api/crm/v1" in svar.json()["detail"]
        # Och kan inte skapa en ny nyckel åt sig själv.
        assert (await k.post("/api/crm/nycklar", json={"namn": "x", "omfang": ["crm:admin"]})).status_code == 403


async def test_varje_omfang_oppnar_bara_sitt(buddy):
    las = await buddy.ny_nyckel(["crm:las"])
    async with buddy.klient(las) as k:
        assert (await k.get(f"{V1}/companies")).status_code == 200
        for metod, vag, kropp in [("post", "/companies", {"name": "X AB"}),
                                  ("post", "/sync/companies", {"connection": "x", "items": [{}]}),
                                  ("post", "/connections", {"name": "x"})]:
            svar = await getattr(k, metod)(f"{V1}{vag}", json=kropp)
            assert svar.status_code == 403 and svar.json()["detail"]["code"] == "scope_missing", vag


async def test_aterkallad_nyckel_slutar_galla(buddy, storage):
    from app.crm import nycklar

    ra = await buddy.ny_nyckel(["crm:las"], namn="tillfällig")
    listan = await nycklar.lista(storage, buddy.id)
    assert {n["namn"] for n in listan} == {"integration", "tillfällig"}
    assert all(n["prefix"].startswith("snajp_crm_") and len(n["prefix"]) < 20 for n in listan)
    rad = next(n for n in listan if n["namn"] == "tillfällig")
    assert await nycklar.aterkalla(storage, buddy.id, rad["id"])
    async with buddy.klient(ra) as k:
        assert (await k.get(f"{V1}/me")).status_code == 401
    # En annan kund kan inte dra in nyckeln.
    assert not await nycklar.aterkalla(storage, "00000000-0000-0000-0000-000000000000", listan[0]["id"])


# -- Tenantisolering ---------------------------------------------------------


async def test_en_kund_ser_aldrig_en_annans_poster(buddy, annan):
    async with buddy.klient() as k:
        bolag = (await k.post(f"{V1}/companies", json={"name": "Hemligt AB", "org_number": ORGNR_A})).json()
        person = (await k.post(f"{V1}/people", json={"email": "vd@hemligt.se", "company_id": bolag["id"]})).json()
        await _anslutning(k)
        korning = (await k.post(f"{V1}/sync/runs", json={"connection": "hubspot"})).json()
    async with annan.klient() as k:
        assert (await k.get(f"{V1}/companies")).json()["data"] == []
        assert (await k.get(f"{V1}/people")).json()["data"] == []
        assert (await k.get(f"{V1}/connections")).json()["data"] == []
        assert (await k.get(f"{V1}/sync/runs")).json()["data"] == []
        for vag in (f"/companies/{bolag['id']}", f"/people/{person['id']}", f"/sync/runs/{korning['id']}",
                    "/connections/hubspot"):
            assert (await k.get(f"{V1}{vag}")).status_code == 404, vag
        assert (await k.patch(f"{V1}/companies/{bolag['id']}", json={"name": "Kapat"})).status_code == 404
        assert (await k.delete(f"{V1}/companies/{bolag['id']}")).status_code == 404
        assert (await k.post(f"{V1}/sync/runs/{korning['id']}/companies", json={"items": [{"id": "1"}]})).status_code == 404
        # Samma organisationsnummer hos en annan kund är en annan post, inte en krock.
        eget = await k.post(f"{V1}/companies", json={"name": "Eget AB", "org_number": ORGNR_A})
        assert eget.status_code == 201 and eget.json()["id"] != bolag["id"]
        # En person kan inte knytas till en annan kunds bolag.
        svar = await k.post(f"{V1}/people", json={"email": "x@y.se", "company_id": bolag["id"]})
        assert svar.status_code == 422 and svar.json()["detail"]["code"] == "company_not_found"
    async with buddy.klient() as k:
        assert (await k.get(f"{V1}/companies/{bolag['id']}")).json()["name"] == "Hemligt AB"


# -- Bolag och personer ------------------------------------------------------


async def test_bolag_skapas_normaliseras_och_uppdateras_pa_orgnr(buddy):
    async with buddy.klient() as k:
        svar = await k.post(f"{V1}/companies", json={
            "name": "Byggarna Berggren AB", "org_number": "16556036-0793", "phone": "08-123 456 78",
            "website": "www.berggren.se", "address": {"postal_code": "11122", "city": "Stockholm"},
            "contract_end": "31/12/2026", "custom": {"kundnummer": "K-17"}})
        assert svar.status_code == 201, svar.text
        b = svar.json()
        assert b["org_number"] == ORGNR_A and b["phone"] == "+46812345678" and b["domain"] == "berggren.se"
        assert b["address"] == {"street": None, "co": None, "postal_code": "111 22", "city": "Stockholm", "country": "SE"}
        assert b["contract_end"] == "2026-12-31" and b["relation"] == "customer" and b["source"] == "api"
        assert b["custom"] == {"kundnummer": "K-17"} and b["sole_proprietor"] is False
        # Samma organisationsnummer igen, annat skrivsätt: samma post, 200.
        igen = await k.post(f"{V1}/companies", json={"name": "Byggarna Berggren AB", "org_number": "5560360793",
                                                     "employees": 12})
        assert igen.status_code == 200 and igen.json()["id"] == b["id"] and igen.json()["employees"] == 12
        assert len((await k.get(f"{V1}/companies")).json()["data"]) == 1
        # Uppslag på orgnr och fritext.
        assert [x["id"] for x in (await k.get(f"{V1}/companies", params={"org_number": "556036-0793"})).json()["data"]] == [b["id"]]
        assert len((await k.get(f"{V1}/companies", params={"q": "berggren"})).json()["data"]) == 1
        assert (await k.get(f"{V1}/companies", params={"q": "finns inte"})).json()["data"] == []


async def test_ogiltiga_falt_ger_422_med_faltnamn(buddy):
    async with buddy.klient() as k:
        svar = await k.post(f"{V1}/companies", json={"name": "X AB", "org_number": "556036-0794",
                                                     "address": {"postal_code": "12"}})
        assert svar.status_code == 422
        d = svar.json()["detail"]
        assert d["code"] == "invalid_fields" and d["message"] and d["meddelande"]
        assert {(f["field"], f["code"]) for f in d["fields"]} == {
            ("org_number", "orgnr_kontrollsiffra"), ("address.postal_code", "postnr_ogiltigt")}
        assert (await k.post(f"{V1}/companies", json={"org_number": ORGNR_A})).status_code == 422  # namn krävs
        assert (await k.post(f"{V1}/companies", json={"name": "X", "okant": 1})).status_code == 422
        assert (await k.get(f"{V1}/companies")).json()["data"] == []


async def test_andra_och_tom_ett_falt(buddy):
    async with buddy.klient() as k:
        b = (await k.post(f"{V1}/companies", json={"name": "X AB", "phone": "08-123 456 78", "org_number": ORGNR_A})).json()
        svar = await k.patch(f"{V1}/companies/{b['id']}", json={"phone": None, "relation": "former_customer",
                                                               "address": {"city": "Umeå"}})
        assert svar.status_code == 200, svar.text
        ny = svar.json()
        assert ny["phone"] is None and ny["relation"] == "former_customer" and ny["address"]["city"] == "Umeå"
        assert ny["org_number"] == ORGNR_A and ny["name"] == "X AB"
        # Ett orgnr som redan tillhör ett annat bolag avvisas.
        await k.post(f"{V1}/companies", json={"name": "Y AB", "org_number": ORGNR_B})
        assert (await k.patch(f"{V1}/companies/{b['id']}", json={"org_number": ORGNR_B})).status_code == 409


async def test_radering_ar_mjuk_och_syns_for_den_som_synkar_ut(buddy):
    async with buddy.klient() as k:
        b = (await k.post(f"{V1}/companies", json={"name": "X AB", "org_number": ORGNR_A})).json()
        assert (await k.delete(f"{V1}/companies/{b['id']}")).status_code == 204
        assert (await k.get(f"{V1}/companies/{b['id']}")).status_code == 404
        assert (await k.get(f"{V1}/companies")).json()["data"] == []
        gravsten = (await k.get(f"{V1}/companies", params={"include_deleted": "true"})).json()["data"]
        assert len(gravsten) == 1 and gravsten[0]["deleted_at"]
        # Numret är ledigt igen för en ny post.
        assert (await k.post(f"{V1}/companies", json={"name": "X AB", "org_number": ORGNR_A})).status_code == 201


async def test_papperskorgen_aterstaller_och_permanent_radering_tommer(buddy, storage):
    async with buddy.klient() as k:
        b = (await k.post(f"{V1}/companies", json={"name": "X AB", "org_number": ORGNR_A})).json()
        p = (await k.post(f"{V1}/people", json={"first_name": "Anna", "email": "anna@x.se", "mobile": "070-123 45 67",
                                                "company_id": b["id"], "custom": {"not": "ringer helst på förmiddagen"}})).json()
        # Ångra en radering.
        await k.delete(f"{V1}/companies/{b['id']}")
        ater = await k.post(f"{V1}/companies/{b['id']}/restore")
        assert ater.status_code == 200 and ater.json()["deleted_at"] is None and ater.json()["org_number"] == ORGNR_A
        # Numret har hunnit tas av en annan post: återställningen krockar i stället för att ge två.
        await k.delete(f"{V1}/companies/{b['id']}")
        await k.post(f"{V1}/companies", json={"name": "Ny X AB", "org_number": ORGNR_A})
        assert (await k.post(f"{V1}/companies/{b['id']}/restore")).status_code == 409

        # Personen ber att bli raderad: allt utom id och tider försvinner direkt.
        assert (await k.delete(f"{V1}/people/{p['id']}", params={"permanent": "true"})).status_code == 204
        grav = (await k.get(f"{V1}/people/{p['id']}", params={"include_deleted": "true"})).json()
        assert grav["id"] == p["id"] and grav["deleted_at"] and grav["source"] == "gravsten"
        assert all(grav[f] is None for f in ("first_name", "email", "mobile", "company_id")) and grav["custom"] == {}
        assert "anna" not in str(storage._crm["crm_personer"][p["id"]]).lower()
        tomd = await k.post(f"{V1}/people/{p['id']}/restore")
        assert tomd.status_code == 410 and tomd.json()["detail"]["code"] == "permanently_deleted"
        assert (await k.delete(f"{V1}/people/{p['id']}", params={"permanent": "true"})).status_code == 404
        # Adressen är ledig för en ny post.
        assert (await k.post(f"{V1}/people", json={"email": "anna@x.se"})).status_code == 201
        assert (await k.post(f"{V1}/companies/{p['id']}/restore")).status_code == 404  # fel objekt


async def test_papperskorgen_toms_efter_trettio_dagar_och_kallans_id_gloms(buddy, storage):
    async with buddy.klient() as k:
        await _anslutning(k)
        ut = (await k.post(f"{V1}/sync/companies", json={"connection": "hubspot", "items": [
            hubspot("1", "Gammal Kund AB", ORGNR_A, phone="08-123 456 78"), hubspot("2", "Annan AB", ORGNR_B)]})).json()
        gammal, annan_id = ut["items"][0]["id"], ut["items"][1]["id"]
        await k.delete(f"{V1}/companies/{gammal}")
        # 31 dagar senare raderas något annat: då töms det som legat för länge.
        storage._crm["crm_bolag"][gammal]["raderad_at"] = "2026-01-01T00:00:00+00:00"
        await k.delete(f"{V1}/companies/{annan_id}")
        grav = (await k.get(f"{V1}/companies/{gammal}", params={"include_deleted": "true"})).json()
        assert grav["source"] == "gravsten" and grav["name"] == "" and grav["org_number"] is None and grav["phone"] is None
        assert grav["external_ids"] == []
        # Den nyss raderade ligger kvar orörd i papperskorgen.
        kvar = (await k.get(f"{V1}/companies/{annan_id}", params={"include_deleted": "true"})).json()
        assert kvar["name"] == "Annan AB" and kvar["org_number"] == ORGNR_B
        # Källan skickar bolaget igen: en ny post, den tömda väcks inte.
        ny = (await k.post(f"{V1}/sync/companies", json={"connection": "hubspot", "items": [
            hubspot("1", "Gammal Kund AB", ORGNR_A)]})).json()
        assert ny["items"][0]["status"] == "created" and ny["items"][0]["id"] != gammal


async def test_en_enskild_firmas_personnummer_sparas_aldrig(buddy, storage):
    """Beslutet 2026-11-23: personnummer sparas inte. Bolaget blir ändå en post."""
    personnummer = "800101-1231"  # giltig kontrollsiffra, tredje siffran under 2
    async with buddy.klient() as k:
        # Direkt i API:t sägs det rakt ut i stället för att tyst tappas.
        svar = await k.post(f"{V1}/companies", json={"name": "Annas Måleri", "org_number": personnummer})
        assert svar.status_code == 422
        assert svar.json()["detail"]["fields"] == [{"field": "org_number", "code": "orgnr_ar_personnummer"}]
        # I en synk skapas bolaget utan nummer, märkt som enskild firma.
        await _anslutning(k)
        ut = (await k.post(f"{V1}/sync/companies", json={"connection": "hubspot", "items": [
            hubspot("1", "Annas Måleri", personnummer, domain="annasmaleri.se")]})).json()
        assert ut["items"][0]["status"] == "created"
        assert ut["items"][0]["field_errors"] == [{"falt": "orgnr", "kod": "orgnr_ar_personnummer", "varde": "(sparas inte)"}]
        bolag = (await k.get(f"{V1}/companies/{ut['items'][0]['id']}")).json()
        assert bolag["org_number"] is None and bolag["sole_proprietor"] is True
        # Varken raden eller körningens fellogg bär numret.
        allt = str(storage._crm)
        assert "800101" not in allt and "8001011231" not in allt
        # Utan nummer känns firman igen på sin domän nästa gång.
        igen = (await k.post(f"{V1}/sync/companies", json={"connection": "hubspot", "items": [
            hubspot("77", "Annas Måleri (ny post i källan)", personnummer, domain="annasmaleri.se")]})).json()
        assert igen["items"][0]["status"] == "updated" and igen["items"][0]["id"] == ut["items"][0]["id"]


async def test_en_adress_med_begransad_behandling_toms_inte(buddy, storage):
    """Art. 18: den som begärt begränsning har bett oss behålla uppgifterna orörda."""
    async with buddy.klient() as k:
        await _anslutning(k, missing_records="delete")
        p = (await k.post(f"{V1}/people", json={"first_name": "Bo", "email": "bo@tvist.se"})).json()
        synkad = (await k.post(f"{V1}/sync/people", json={"connection": "hubspot", "items": [
            {"id": "p9", "properties": {"firstname": "Eva", "email": "eva@tvist.se"}}]})).json()
        storage.behandlingsbegransningar.extend([
            {"email": "bo@tvist.se", "havd_at": None}, {"email": "eva@tvist.se", "havd_at": None}])
        # Permanent radering vägras, med en kod integrationen kan grena på.
        svar = await k.delete(f"{V1}/people/{p['id']}", params={"permanent": "true"})
        assert svar.status_code == 409 and svar.json()["detail"]["code"] == "processing_restricted"
        # Vanlig radering går (den går att ångra), men trettio dagar tömmer inte raden.
        assert (await k.delete(f"{V1}/people/{p['id']}")).status_code == 204
        storage._crm["crm_personer"][p["id"]]["raderad_at"] = "2026-01-01T00:00:00+00:00"
        annan = (await k.post(f"{V1}/people", json={"email": "annan@a.se"})).json()
        await k.delete(f"{V1}/people/{annan['id']}")
        assert storage._crm["crm_personer"][p["id"]]["epost"] == "bo@tvist.se"
        # En full synk där personen saknas raderar henne inte heller.
        korning = (await k.post(f"{V1}/sync/runs", json={"connection": "hubspot", "mode": "full"})).json()
        await k.post(f"{V1}/sync/runs/{korning['id']}/people", json={"items": [
            {"id": "p10", "properties": {"email": "ny@a.se"}}]})
        klar = (await k.post(f"{V1}/sync/runs/{korning['id']}/complete")).json()
        assert klar["counts"]["removed"] == 0
        assert (await k.get(f"{V1}/people/{synkad['items'][0]['id']}")).json()["email"] == "eva@tvist.se"
        # Och en begränsad adress synkas inte in på nytt.
        ny = (await k.post(f"{V1}/sync/people", json={"connection": "hubspot", "items": [
            {"id": "p11", "properties": {"email": "bo@tvist.se"}}]})).json()
        assert ny["items"][0]["status"] == "skipped" and ny["items"][0]["reason"] == "behandlingen_ar_begransad"


async def test_personer_knyts_till_bolag_och_uppdateras_pa_epost(buddy):
    async with buddy.klient() as k:
        b = (await k.post(f"{V1}/companies", json={"name": "X AB", "org_number": ORGNR_A})).json()
        p = await k.post(f"{V1}/people", json={"first_name": "Anna", "last_name": "Berg", "email": "Anna@X.se",
                                               "mobile": "070-123 45 67", "company_id": b["id"],
                                               "legal_basis": "legitimate_interest"})
        assert p.status_code == 201, p.text
        person = p.json()
        assert person["email"] == "anna@x.se" and person["mobile"] == "+46701234567"
        assert person["legal_basis"] == "legitimate_interest" and person["company_id"] == b["id"]
        igen = await k.post(f"{V1}/people", json={"email": "anna@x.se", "title": "VD"})
        assert igen.status_code == 200 and igen.json()["id"] == person["id"] and igen.json()["title"] == "VD"
        per_bolag = (await k.get(f"{V1}/people", params={"company_id": b["id"]})).json()["data"]
        assert [x["id"] for x in per_bolag] == [person["id"]]
        assert (await k.post(f"{V1}/people", json={"title": "VD"})).status_code == 422


async def test_sidindelning_med_markor(buddy):
    async with buddy.klient() as k:
        for i in range(7):
            assert (await k.post(f"{V1}/companies", json={"name": f"Bolag {i} AB"})).status_code == 201
        sedda, markor = [], None
        for _ in range(5):
            sida = (await k.get(f"{V1}/companies", params={"limit": 3, "sort": "name", **({"cursor": markor} if markor else {})})).json()
            sedda += [b["name"] for b in sida["data"]]
            markor = sida["next_cursor"]
            if not markor:
                break
        assert sedda == [f"Bolag {i} AB" for i in range(7)]
        assert (await k.get(f"{V1}/companies", params={"cursor": "skrap"})).status_code == 422
        # Ändringsordning med updated_since: det den som synkar ut frågar efter.
        nyast = (await k.get(f"{V1}/companies", params={"limit": 500})).json()["data"][-1]
        sedan = (await k.get(f"{V1}/companies", params={"updated_since": nyast["updated_at"]})).json()["data"]
        assert [b["id"] for b in sedan] == [nyast["id"]]


# -- Synken ------------------------------------------------------------------


async def test_synk_i_ett_anrop_och_omsynk_andrar_ingenting(buddy):
    async with buddy.klient() as k:
        await _anslutning(k)
        sats = {"connection": "hubspot", "items": [
            hubspot("1", "Byggarna Berggren AB", ORGNR_A, phone="08-123 456 78", city="Stockholm"),
            hubspot("2", "Måleri Nord AB", ORGNR_B),
            hubspot("3", "", None),                      # saknar namn: hoppas över
            hubspot("4", "Fel Nummer AB", "556036-0794"),  # fel kontrollsiffra: bolaget skapas, fältet hoppas
        ]}
        svar = await k.post(f"{V1}/sync/companies", json=sats)
        assert svar.status_code == 200, svar.text
        ut = svar.json()
        assert ut["counts"] == {"total": 4, "created": 3, "updated": 0, "unchanged": 0, "skipped": 1,
                                "conflicts": 0, "removed": 0}
        assert [p["status"] for p in ut["items"]] == ["created", "created", "skipped", "created"]
        assert ut["items"][2]["reason"] == "saknar_namn"
        assert ut["items"][3]["field_errors"][0]["kod"] == "orgnr_kontrollsiffra"
        assert ut["run"]["status"] == "completed" and ut["run"]["mode"] == "delta"
        # Felen finns kvar på körningen, så att de går att läsa efter en omladdning.
        korning = (await k.get(f"{V1}/sync/runs/{ut['run']['id']}")).json()
        assert korning["counts"]["created"] == 3 and len(korning["errors"]) == 2

        bolag = (await k.get(f"{V1}/companies", params={"org_number": ORGNR_A})).json()["data"][0]
        assert bolag["source"] == "synk" and bolag["relation"] == "customer" and bolag["phone"] == "+46812345678"
        assert bolag["external_ids"][0]["connection"] == "hubspot" and bolag["external_ids"][0]["id"] == "1"

        # Samma sats igen: inga dubbletter, inga ändringar.
        igen = (await k.post(f"{V1}/sync/companies", json=sats)).json()
        assert igen["counts"]["created"] == 0 and igen["counts"]["unchanged"] == 3
        assert len((await k.get(f"{V1}/companies")).json()["data"]) == 3

        # En ändring i källan: en uppdatering.
        sats["items"][0]["properties"]["city"] = "Göteborg"
        andrad = (await k.post(f"{V1}/sync/companies", json=sats)).json()
        assert andrad["counts"]["updated"] == 1 and andrad["counts"]["unchanged"] == 2
        assert (await k.get(f"{V1}/companies/{bolag['id']}")).json()["address"]["city"] == "Göteborg"


async def test_tva_kallor_om_samma_bolag_blir_en_post(buddy):
    async with buddy.klient() as k:
        await _anslutning(k, "hubspot")
        await k.post(f"{V1}/connections", json={"name": "fortnox", "system": "fortnox"})
        await k.post(f"{V1}/sync/companies", json={"connection": "hubspot", "items": [hubspot("h1", "Berggren AB", ORGNR_A)]})
        svar = await k.post(f"{V1}/sync/companies", json={"connection": "fortnox", "items": [
            {"CustomerNumber": "1001", "Name": "Byggarna Berggren Aktiebolag", "OrganisationNumber": ORGNR_A,
             "Email": "faktura@berggren.se", "Active": True, "Type": "COMPANY"},
            {"CustomerNumber": "1002", "Name": "Anna Berg", "Type": "PRIVATE"}]})
        ut = svar.json()
        assert [p["status"] for p in ut["items"]] == ["updated", "skipped"]
        alla = (await k.get(f"{V1}/companies")).json()["data"]
        assert len(alla) == 1 and alla[0]["email"] == "faktura@berggren.se"
        assert {e["connection"] for e in alla[0]["external_ids"]} == {"hubspot", "fortnox"}


async def test_utan_orgnr_matchas_bara_pa_entydig_doman_eller_entydigt_namn(buddy):
    async with buddy.klient() as k:
        await _anslutning(k)
        await k.post(f"{V1}/companies", json={"name": "Bygg AB", "website": "bygg-norr.se"})
        await k.post(f"{V1}/companies", json={"name": "Bygg AB", "website": "bygg-syd.se"})
        await k.post(f"{V1}/companies", json={"name": "Ensam AB"})
        ut = (await k.post(f"{V1}/sync/companies", json={"connection": "hubspot", "items": [
            hubspot("1", "Bygg Norr", domain="bygg-norr.se"),   # entydig domän: samma post
            hubspot("2", "Bygg AB"),                             # två heter så: ny post, ingen gissning
            hubspot("3", "ENSAM aktiebolag"),                    # entydigt namn utan bolagsform: samma post
            hubspot("4", "Gmail-firman", domain="gmail.com"),    # privat domän matchar aldrig
        ]})).json()
        assert [p["status"] for p in ut["items"]] == ["updated", "created", "updated", "created"]


async def test_orgnr_som_tillhor_ett_annat_bolag_ar_en_konflikt(buddy):
    async with buddy.klient() as k:
        await _anslutning(k)
        await k.post(f"{V1}/sync/companies", json={"connection": "hubspot", "items": [
            hubspot("1", "A AB", ORGNR_A), hubspot("2", "B AB", ORGNR_B)]})
        ut = (await k.post(f"{V1}/sync/companies", json={"connection": "hubspot", "items": [
            hubspot("1", "A AB", ORGNR_B, updatedAt="2026-11-21T08:00:00Z")]})).json()
        assert ut["items"][0]["status"] == "conflict" and ut["items"][0]["reason"] == "orgnr_tillhor_annat_bolag"
        assert ut["run"]["counts"]["conflicts"] == 1


@pytest.mark.parametrize("regel,kallans_tid,vantat", [
    ("source_wins", "2026-01-01T00:00:00Z", "08-999 99 99"),
    ("snajp_wins", "2099-01-01T00:00:00Z", "070-111 11 11"),
    ("newest_wins", "2020-01-01T00:00:00Z", "070-111 11 11"),   # handändringen är nyare
    ("newest_wins", "2099-01-01T00:00:00Z", "08-999 99 99"),    # källan är nyare
])
async def test_konfliktregeln_avgor_falt_for_falt(buddy, regel, kallans_tid, vantat):
    from app.crm import falt

    async with buddy.klient() as k:
        await _anslutning(k, conflict_rule=regel)
        ut = (await k.post(f"{V1}/sync/companies", json={"connection": "hubspot", "items": [
            hubspot("1", "A AB", ORGNR_A, phone="08-123 456 78", city="Stockholm")]})).json()
        bolag_id = ut["items"][0]["id"]
        # Någon rättar telefonnumret för hand i Snajp.
        await k.patch(f"{V1}/companies/{bolag_id}", json={"phone": "070-111 11 11"})
        ny = (await k.post(f"{V1}/sync/companies", json={"connection": "hubspot", "items": [
            hubspot("1", "A AB", ORGNR_A, phone="08-999 99 99", city="Umeå", updatedAt=kallans_tid)]})).json()
        bolag = (await k.get(f"{V1}/companies/{bolag_id}")).json()
        assert bolag["phone"] == falt.telefon(vantat)
        # Orten har ingen rört för hand: den följer alltid källan.
        assert bolag["address"]["city"] == "Umeå"
        assert ("phone" not in str(ny["items"][0].get("kept_fields"))) and (
            (ny["items"][0].get("kept_fields") == ["telefon"]) == (vantat == "070-111 11 11"))


async def test_ett_falt_kallan_inte_skickar_roers_inte(buddy):
    async with buddy.klient() as k:
        await _anslutning(k)
        ut = (await k.post(f"{V1}/sync/companies", json={"connection": "hubspot", "items": [
            hubspot("1", "A AB", ORGNR_A, phone="08-123 456 78", city="Stockholm")]})).json()
        await k.post(f"{V1}/sync/companies", json={"connection": "hubspot", "items": [hubspot("1", "A AB", ORGNR_A)]})
        bolag = (await k.get(f"{V1}/companies/{ut['items'][0]['id']}")).json()
        assert bolag["phone"] == "+46812345678" and bolag["address"]["city"] == "Stockholm"


async def test_full_synk_i_satser_tar_hand_om_det_som_saknas(buddy):
    async with buddy.klient() as k:
        await _anslutning(k, missing_records="mark_former_customer")
        await k.post(f"{V1}/sync/companies", json={"connection": "hubspot", "items": [
            hubspot("1", "A AB", ORGNR_A), hubspot("2", "B AB", ORGNR_B), hubspot("3", "C AB", ORGNR_C)]})
        # Nattens fulla synk: C finns inte kvar hos källan.
        korning = (await k.post(f"{V1}/sync/runs", json={"connection": "hubspot", "mode": "full"})).json()
        assert korning["status"] == "processing"
        await k.post(f"{V1}/sync/runs/{korning['id']}/companies", json={"items": [hubspot("1", "A AB", ORGNR_A)]})
        await k.post(f"{V1}/sync/runs/{korning['id']}/companies", json=[hubspot("2", "B AB", ORGNR_B)])
        klar = (await k.post(f"{V1}/sync/runs/{korning['id']}/complete")).json()
        assert klar["status"] == "completed" and klar["counts"]["total"] == 2 and klar["counts"]["removed"] == 1
        relationer = {b["name"]: b["relation"] for b in (await k.get(f"{V1}/companies")).json()["data"]}
        assert relationer == {"A AB": "customer", "B AB": "customer", "C AB": "former_customer"}
        # En avslutad körning tar inte emot fler satser.
        sen = await k.post(f"{V1}/sync/runs/{korning['id']}/companies", json={"items": [hubspot("9", "Z AB")]})
        assert sen.status_code == 409 and sen.json()["detail"]["code"] == "run_closed"
        assert (await k.get(f"{V1}/connections/hubspot")).json()["last_sync_at"]


async def test_tom_full_synk_tommer_inte_registret(buddy):
    async with buddy.klient() as k:
        await _anslutning(k, missing_records="delete")
        await k.post(f"{V1}/sync/companies", json={"connection": "hubspot", "items": [hubspot("1", "A AB", ORGNR_A)]})
        korning = (await k.post(f"{V1}/sync/runs", json={"connection": "hubspot", "mode": "full"})).json()
        klar = (await k.post(f"{V1}/sync/runs/{korning['id']}/complete")).json()
        assert klar["status"] == "failed" and klar["error"] == "tom_full_synk"
        assert len((await k.get(f"{V1}/companies")).json()["data"]) == 1


async def test_raderad_i_kallan_blir_gravsten_och_kan_komma_tillbaka(buddy):
    async with buddy.klient() as k:
        await _anslutning(k)
        ut = (await k.post(f"{V1}/sync/companies", json={"connection": "hubspot", "items": [hubspot("1", "A AB", ORGNR_A)]})).json()
        bort = (await k.post(f"{V1}/sync/companies", json={"connection": "hubspot", "items": [
            hubspot("1", "A AB", ORGNR_A, archived=True)]})).json()
        assert bort["items"][0]["status"] == "removed"
        assert (await k.get(f"{V1}/companies")).json()["data"] == []
        ater = (await k.post(f"{V1}/sync/companies", json={"connection": "hubspot", "items": [hubspot("1", "A AB", ORGNR_A)]})).json()
        assert ater["items"][0]["status"] == "updated" and ater["items"][0]["id"] == ut["items"][0]["id"]
        assert len((await k.get(f"{V1}/companies")).json()["data"]) == 1


async def test_personer_synkas_och_knyts_via_kallans_bolags_id(buddy, storage):
    await storage.add_suppression(buddy.id, email="avregistrerad@a.se", reason="avregistrering")
    storage.begransningar = getattr(storage, "begransningar", [])
    async with buddy.klient() as k:
        await _anslutning(k)
        bolag = (await k.post(f"{V1}/sync/companies", json={"connection": "hubspot", "items": [hubspot("c1", "A AB", ORGNR_A)]})).json()
        ut = (await k.post(f"{V1}/sync/people", json={"connection": "hubspot", "items": [
            {"id": "p1", "properties": {"firstname": "Anna", "lastname": "Berg", "email": "Anna@A.se",
                                        "mobilephone": "070-123 45 67", "associatedcompanyid": "c1"}},
            {"id": "p2", "properties": {"email": "avregistrerad@a.se", "associatedcompanyid": "c1"}},
            {"id": "p3", "properties": {"jobtitle": "VD"}},
        ]})).json()
        assert [p["status"] for p in ut["items"]] == ["created", "created", "skipped"]
        personer = {p["email"]: p for p in (await k.get(f"{V1}/people")).json()["data"]}
        assert personer["anna@a.se"]["company_id"] == bolag["items"][0]["id"]
        assert personer["anna@a.se"]["mobile"] == "+46701234567" and personer["anna@a.se"]["do_not_contact"] is False
        # Den som avregistrerat sig hos kunden får märket med sig in i CRM:et.
        assert personer["avregistrerad@a.se"]["do_not_contact"] is True


async def test_csv_in_med_anslutningen_i_fragan(buddy):
    async with buddy.klient() as k:
        await k.post(f"{V1}/connections", json={"name": "export", "system": "generisk"})
        csv = ("Kundnummer;Företag;Org.nr;Telefon;Postnummer;Ort;Avtalsslut\n"
               f"1001;Buddy Kund AB;{ORGNR_A};08-123 456 78;111 22;Stockholm;2027-03-31\n"
               f"1002;Andra Kunden AB;{ORGNR_B};;903 26;Umeå;\n")
        svar = await k.post(f"{V1}/sync/companies", params={"connection": "export"}, content=csv.encode(),
                            headers={"Content-Type": "text/csv; charset=utf-8"})
        assert svar.status_code == 200, svar.text
        assert svar.json()["counts"]["created"] == 2
        b = (await k.get(f"{V1}/companies", params={"org_number": ORGNR_A})).json()["data"][0]
        assert b["contract_end"] == "2027-03-31" and b["external_ids"][0]["id"] == "1001"


async def test_forhandsgranskning_skriver_ingenting(buddy):
    async with buddy.klient() as k:
        await _anslutning(k)
        svar = await k.post(f"{V1}/connections/hubspot/preview", json={
            "items": [{"id": "1", "properties": {"name": "A AB", "svenskt_orgnr": ORGNR_A}}],
            "mapping": {"bolag": {"orgnr": "properties.svenskt_orgnr"}}})
        assert svar.status_code == 200, svar.text
        post = svar.json()["items"][0]
        assert post["status"] == "created" and post["interpreted"]["orgnr"] == ORGNR_A
        assert (await k.get(f"{V1}/companies")).json()["data"] == []
        assert (await k.get(f"{V1}/sync/runs")).json()["data"] == []
        # Mappningen sparades inte: utan den hittas inget orgnr.
        utan = (await k.post(f"{V1}/connections/hubspot/preview", json={
            "items": [{"id": "1", "properties": {"name": "A AB", "svenskt_orgnr": ORGNR_A}}]})).json()
        assert "orgnr" not in utan["items"][0]["interpreted"]
        fel = await k.post(f"{V1}/connections/hubspot/preview", json={"items": [], "mapping": {"bolag": {"finns_inte": "x"}}})
        assert fel.status_code == 422 and fel.json()["detail"]["code"] == "invalid_mapping"


async def test_satsens_granser(buddy):
    async with buddy.klient() as k:
        await _anslutning(k)
        for kropp, kod in [({"connection": "hubspot", "items": []}, "empty_batch"),
                           ({"connection": "hubspot", "items": [{}] * (crm_v1.MAX_SATS + 1)}, "too_many_items"),
                           ({"items": [{}]}, "connection_required"),
                           ({"connection": "saknas", "items": [{}]}, "connection_not_found")]:
            svar = await k.post(f"{V1}/sync/companies", json=kropp)
            assert svar.json()["detail"]["code"] == kod, kod
        assert (await k.post(f"{V1}/sync/companies", content=b"{inte json", headers={"Content-Type": "application/json"})).status_code == 422


# -- Idempotens, tak och avtal -----------------------------------------------


async def test_idempotency_key_ger_samma_svar_en_gang(buddy):
    async with buddy.klient() as k:
        h = {"Idempotency-Key": "skapa-berggren-1"}
        forsta = await k.post(f"{V1}/companies", json={"name": "A AB"}, headers=h)
        andra = await k.post(f"{V1}/companies", json={"name": "A AB"}, headers=h)
        assert forsta.status_code == andra.status_code == 201
        assert forsta.json() == andra.json() and andra.headers["Idempotent-Replayed"] == "true"
        assert len((await k.get(f"{V1}/companies")).json()["data"]) == 1
        # Samma nyckel med annan kropp är anroparens fel, inte ett tyst återspelat svar.
        annan = await k.post(f"{V1}/companies", json={"name": "B AB"}, headers=h)
        assert annan.status_code == 422 and annan.json()["detail"]["code"] == "idempotency_key_reused"
        # Utan nyckel skapas en post per anrop (bolag utan orgnr har ingen naturlig nyckel).
        await k.post(f"{V1}/companies", json={"name": "A AB"})
        assert len((await k.get(f"{V1}/companies")).json()["data"]) == 2


async def test_idempotensnyckeln_ar_kundens_egen(buddy, annan):
    h = {"Idempotency-Key": "samma-nyckel"}
    async with buddy.klient() as k:
        ett = (await k.post(f"{V1}/companies", json={"name": "A AB"}, headers=h)).json()
    async with annan.klient() as k:
        tva = await k.post(f"{V1}/companies", json={"name": "A AB"}, headers=h)
        assert tva.status_code == 201 and "Idempotent-Replayed" not in tva.headers and tva.json()["id"] != ett["id"]


async def test_taket_ger_429_med_retry_after(buddy, monkeypatch):
    monkeypatch.setattr(crm_v1, "_TAK", crm_v1.RateLimitRule(max_requests=3, window_seconds=60))
    async with buddy.klient() as k:
        svar = [await k.get(f"{V1}/me") for _ in range(4)]
        assert [s.status_code for s in svar] == [200, 200, 200, 429]
        assert svar[0].headers["X-RateLimit-Limit"] == "3" and svar[2].headers["X-RateLimit-Remaining"] == "0"
        assert svar[3].headers["Retry-After"] == "60" and svar[3].json()["detail"]["code"] == "rate_limited"


async def test_taket_ar_per_kund(buddy, annan, monkeypatch):
    monkeypatch.setattr(crm_v1, "_TAK", crm_v1.RateLimitRule(max_requests=1, window_seconds=60))
    async with buddy.klient() as k:
        assert (await k.get(f"{V1}/me")).status_code == 200
        assert (await k.get(f"{V1}/me")).status_code == 429
    async with annan.klient() as k:
        assert (await k.get(f"{V1}/me")).status_code == 200


async def test_utan_registrerat_avtal_gar_det_att_lasa_men_inte_skriva(utan_avtal):
    async with utan_avtal.klient() as k:
        assert (await k.get(f"{V1}/companies")).status_code == 200
        for vag, kropp in [("/companies", {"name": "A AB"}), ("/people", {"email": "a@b.se"}),
                           ("/sync/companies", {"connection": "x", "items": [{}]}),
                           ("/sync/runs", {"connection": "x"})]:
            svar = await k.post(f"{V1}{vag}", json=kropp)
            assert svar.status_code == 403 and svar.json()["detail"]["code"] == "agreement_missing", vag


# -- Kopplingen till leads ---------------------------------------------------


async def test_bolag_i_crm_ar_upptagna_for_iris_och_listbygget(buddy, annan, storage):
    """Det Buddy behöver: kunderna som synkats in hämtas aldrig som leads."""
    async with buddy.klient() as k:
        await _anslutning(k)
        ut = (await k.post(f"{V1}/sync/companies", json={"connection": "hubspot", "items": [
            hubspot("1", "Byggarna Berggren AB", ORGNR_A), hubspot("2", "Utan Nummer AB")]})).json()
        sedda = await upptagna.hamta(storage, buddy.id)
        assert upptagna.upptagen(sedda, "Helt Annat Namn AB", "16556036-0793")     # på orgnr
        assert upptagna.upptagen(sedda, "utan nummer")                             # på namn utan bolagsform
        assert not upptagna.upptagen(sedda, "Okänt Bolag AB", ORGNR_C)
        rader = await storage.lista_upptagna_bolag(buddy.id)
        assert {r["kalla"] for r in rader} == {"crm"} and len(rader) == 2
        # Den andra kundens körningar påverkas inte.
        assert not upptagna.upptagen(await upptagna.hamta(storage, annan.id), "Byggarna Berggren AB", ORGNR_A)
        # Ett raderat bolag är ledigt igen.
        await k.delete(f"{V1}/companies/{ut['items'][0]['id']}")
        assert not upptagna.upptagen(await upptagna.hamta(storage, buddy.id), "Helt Annat Namn AB", ORGNR_A)


# -- Appens egen yta och specifikationen -------------------------------------


async def test_appens_nyckelhantering_och_oversikt(buddy, storage):
    """Appen når /api/crm med kundens egen backendnyckel (omfång *)."""
    await storage.create_api_key(buddy.id, tenant_name="Buddy", raw_key="snajp_live_appens_egen_nyckel")
    async with buddy.klient("snajp_live_appens_egen_nyckel") as k:
        ny = await k.post("/api/crm/nycklar", json={"namn": "Buddys CRM", "omfang": ["crm:las", "crm:synk"]})
        assert ny.status_code == 201 and ny.json()["api_key"].startswith("snajp_crm_")
        listan = (await k.get("/api/crm/nycklar")).json()["nycklar"]
        assert {n["namn"] for n in listan} == {"integration", "Buddys CRM"} and "api_key" not in listan[0]
        # Backendnyckeln själv visas inte och går inte att dra in härifrån.
        assert all(n["omfang"] != ["*"] for n in listan)
        assert (await k.post("/api/crm/nycklar", json={"namn": "x", "omfang": ["*"]})).status_code == 422
        # Den fulla nyckeln når också det versionerade API:t.
        await k.post(f"{V1}/companies", json={"name": "A AB", "org_number": ORGNR_A})
        oversikt = (await k.get("/api/crm/oversikt")).json()
        assert oversikt["bolag"] == {"kund": 1, "alla": 1} and oversikt["personer"] == 0
        nyckel_id = next(n["id"] for n in listan if n["namn"] == "Buddys CRM")
        assert (await k.delete(f"/api/crm/nycklar/{nyckel_id}")).status_code == 204
        assert (await k.delete(f"/api/crm/nycklar/{nyckel_id}")).status_code == 404
        assert (await k.delete("/api/crm/nycklar/inte-ett-uuid")).status_code == 404


async def test_specifikationen_tacker_varje_vag_och_kraver_nyckel(buddy):
    async with buddy.klient("") as k:
        assert (await k.get(f"{V1}/openapi.json")).status_code == 401
    async with buddy.klient() as k:
        spec = (await k.get(f"{V1}/openapi.json")).json()
    assert spec["info"]["title"] == "Snajp CRM API" and spec["security"] == [{"ApiKey": []}]
    vagar = {f"{metod.upper()} {vag}" for vag, metoder in spec["paths"].items() for metod in metoder}
    registrerade = {f"{m} {r.path}" for r in crm_v1.router.routes for m in r.methods if r.include_in_schema}
    assert vagar == registrerade and len(vagar) >= 25
    # Varje väg har en sammanfattning, och satserna dokumenterar både JSON och CSV.
    assert all(op.get("summary") for metoder in spec["paths"].values() for op in metoder.values())
    sats = spec["paths"][f"{V1}/sync/companies"]["post"]["requestBody"]["content"]
    assert set(sats) == {"application/json", "text/csv"}


async def test_felformat_id_ger_404_aldrig_500(buddy):
    async with buddy.klient() as k:
        for vag in ("/companies/inte-ett-uuid", "/people/123", "/sync/runs/zzz"):
            assert (await k.get(f"{V1}{vag}")).status_code == 404, vag


async def test_lagret_tal_att_tabellerna_saknas():
    """Koden får ligga före migrationen: läsvägarna ger då tomt, inte fel."""

    class SaknarTabell(Exception):
        sqlstate = "42P01"

    class Anslutning:
        async def fetch(self, *a, **k):
            raise SaknarTabell()

        fetchrow = fetch

    class Skopad:
        async def __aenter__(self):
            return Anslutning()

        async def __aexit__(self, *a):
            return False

    class Lager:
        pool = object()

        def _scoped(self, tenant_id):
            return Skopad()

    lager, t = Lager(), "00000000-0000-0000-0000-000000000001"
    assert await lagring.upptagna_rader(lager, t) == []
    assert await lagring.lista_anslutningar(lager, t) == []
    assert await lagring.lista_poster(lager, t, "bolag") == ([], None)
    assert await lagring.rakna_poster(lager, t, "bolag") == {"alla": 0}
    assert await lagring.las_idempotens(lager, t, "x") is None
