"""Migration 165: relationen ej aktuell, förlustorsaken ur en lista och
personens källa och insamlingsdag (GDPR art. 14).

Antons beslut 2026-11-27 (docs/crm/SVENSK-STANDARD.md § 4).
"""

from __future__ import annotations

import pytest

from app.crm import adaptrar, lagring
from app.leads import upptagna

from .conftest import ORGNR_A, ORGNR_B

V1 = "/api/crm/v1"
pytestmark = pytest.mark.anyio


def _faltfel(svar) -> list[dict]:
    assert svar.status_code == 422, svar.text
    assert svar.json()["detail"]["code"] == "invalid_fields"
    return svar.json()["detail"]["fields"]


# -- 1. Relationen ej aktuell ------------------------------------------------


async def test_ej_aktuell_skrivs_och_lases_som_not_relevant(buddy, annan, storage):
    async with buddy.klient() as k:
        svar = await k.post(f"{V1}/companies", json={"name": "Nej Tack AB", "org_number": ORGNR_A,
                                                     "relation": "not_relevant"})
        assert svar.status_code == 201, svar.text
        assert svar.json()["relation"] == "not_relevant"
        await k.post(f"{V1}/companies", json={"name": "Kund AB", "org_number": ORGNR_B})
        valda = (await k.get(f"{V1}/companies", params={"relation": "not_relevant"})).json()["data"]
        assert [b["name"] for b in valda] == ["Nej Tack AB"]
    rad = (await lagring.hitta_poster(storage, buddy.id, "bolag", "orgnr_nyckel", ["5560360793"]))[0]
    assert rad["relation"] == "ej_aktuell"
    # Den andra kunden ser inget av det.
    async with annan.klient() as k:
        assert (await k.get(f"{V1}/companies", params={"relation": "not_relevant"})).json()["data"] == []


async def test_ej_aktuell_ar_upptagen_for_iris_men_tidigare_kund_ar_fri(buddy, annan, storage):
    async with buddy.klient() as k:
        await k.post(f"{V1}/companies", json={"name": "Nej Tack AB", "org_number": ORGNR_A,
                                              "relation": "not_relevant"})
        await k.post(f"{V1}/companies", json={"name": "Gammal Kund AB", "org_number": ORGNR_B,
                                              "relation": "former_customer"})
    sedda = await upptagna.hamta(storage, buddy.id)
    assert upptagna.upptagen(sedda, "Helt Annat Namn AB", ORGNR_A)
    assert not upptagna.upptagen(sedda, "Gammal Kund AB", ORGNR_B)
    rader = await lagring.upptagna_rader(storage, buddy.id)
    assert [r["company_name"] for r in rader] == ["Nej Tack AB"]
    assert lagring.upptagen_rad({"namn": "X AB", "relation": "ej_aktuell"}) is not None
    assert not upptagna.upptagen(await upptagna.hamta(storage, annan.id), "Nej Tack AB", ORGNR_A)


async def test_oversikten_raknar_ej_aktuell_och_kundlistan_tar_inte_med_bolaget(buddy, annan, storage):
    # Översikten (/api/crm) når bara kundens egen nyckel, aldrig en med omfång.
    await storage.create_api_key(buddy.id, tenant_name="Buddy", raw_key="snajp_live_buddys_egen")
    await storage.create_api_key(annan.id, tenant_name="Annan Kund AB", raw_key="snajp_live_annans_egen")
    async with buddy.klient("snajp_live_buddys_egen") as k:
        await k.post(f"{V1}/companies", json={"name": "Kund AB"})
        await k.post(f"{V1}/companies", json={"name": "Nej Tack AB", "org_number": ORGNR_A,
                                              "relation": "not_relevant"})
        oversikt = (await k.get("/api/crm/oversikt")).json()
        assert oversikt["bolag"] == {"kund": 1, "ej_aktuell": 1, "alla": 2}
    # Ett vunnet lead för samma bolag står kvar under Iris: relationen gör det inte till en egen kund.
    lead = await storage.create_prospect(buddy.id, company_name="Nej Tack AB", contact_email="vd@nejtack.se")
    await storage.update_prospect(buddy.id, lead["id"], orgnr=ORGNR_A, status="won")
    async with buddy.klient() as k:
        lista = (await k.get(f"{V1}/customers")).json()
        assert lista["counts"] == {"own": 1, "iris": 1}
        assert [(r["origin"], r["name"]) for r in lista["data"]] == [("own", "Kund AB"), ("iris", "Nej Tack AB")]
    async with annan.klient("snajp_live_annans_egen") as k:
        assert (await k.get("/api/crm/oversikt")).json()["bolag"] == {"alla": 0}


def test_kallornas_motsvarighet_till_ej_aktuell_mappas_dit():
    lime = adaptrar.gallande_mappning("lime", None)
    for status in ("notinterested", "declined"):
        assert adaptrar.mappa({"_id": "1", "name": "A AB", "buyingstatus": status}, "bolag", lime).falt[
            "relation"] == "ej_aktuell"
    upsales = adaptrar.gallande_mappning("upsales", None)
    assert adaptrar.mappa({"id": 1, "name": "A AB", "journeyStep": "disqualified"}, "bolag", upsales).falt[
        "relation"] == "ej_aktuell"
    generisk = adaptrar.gallande_mappning("generisk", None)
    for varde in ("Ej aktuell", "not_relevant", "ej_aktuell"):
        assert adaptrar.mappa({"name": "A AB", "relation": varde}, "bolag", generisk).falt["relation"] == "ej_aktuell"
    # Lime Gos "ingen relation" är inget nej.
    lime_go = adaptrar.gallande_mappning("lime_go", None)
    assert adaptrar.mappa({"id": 1, "name": "A AB", "relation": "norelation"}, "bolag", lime_go).falt[
        "relation"] == "ovrigt"


# -- 2. Förlustorsak ur en lista ---------------------------------------------


async def _steg(k) -> dict[str, dict]:
    return {s["name"]: s for s in (await k.get(f"{V1}/deal-stages")).json()["data"]}


async def test_forlustorsak_ur_lista_med_fritext_som_reserv(buddy, annan, storage):
    async with buddy.klient() as k:
        forlorad = (await _steg(k))["Förlorad"]
        svar = await k.post(f"{V1}/deals", json={"name": "Växel", "stage_id": forlorad["id"],
                                                 "lost_reason_code": "price", "lost_reason": "Valde billigare"})
        assert svar.status_code == 201, svar.text
        affar = svar.json()
        assert affar["lost_reason_code"] == "price" and affar["lost_reason"] == "Valde billigare"
        rad = await lagring.hamta_post(storage, buddy.id, "affar", affar["id"])
        assert rad["forlustorsak_kod"] == "pris"
        # Koden byts, fritexten står kvar; null tömmer koden.
        andrad = (await k.patch(f"{V1}/deals/{affar['id']}", json={"lost_reason_code": "competitor"})).json()
        assert andrad["lost_reason_code"] == "competitor" and andrad["lost_reason"] == "Valde billigare"
        historik = (await k.get(f"{V1}/deals/{affar['id']}/history")).json()["data"]
        assert historik[0]["fields"] == ["lost_reason_code"]
        ingen = (await k.post(f"{V1}/deals", json={"name": "Utan orsak"})).json()
        assert ingen["lost_reason_code"] is None
        # Filtret.
        traffar = (await k.get(f"{V1}/deals", params={"lost_reason_code": "competitor"})).json()["data"]
        assert [a["id"] for a in traffar] == [affar["id"]]
        assert (await k.get(f"{V1}/deals", params={"lost_reason_code": "timing"})).json()["data"] == []
        assert (await k.get(f"{V1}/deals", params={"lost_reason_code": "okand"})).status_code == 422
        tom = (await k.patch(f"{V1}/deals/{affar['id']}", json={"lost_reason_code": None})).json()
        assert tom["lost_reason_code"] is None and tom["lost_reason"] == "Valde billigare"
    async with annan.klient() as k:
        assert (await k.get(f"{V1}/deals", params={"lost_reason_code": "competitor"})).json()["data"] == []


async def test_okand_forlustorsak_avvisas(buddy):
    async with buddy.klient() as k:
        falten = _faltfel(await k.post(f"{V1}/deals", json={"name": "Växel", "lost_reason_code": "vadret"}))
        assert falten == [{"field": "lost_reason_code", "code": "forlustorsak_okand"}]
        affar = (await k.post(f"{V1}/deals", json={"name": "Växel"})).json()
        falten = _faltfel(await k.patch(f"{V1}/deals/{affar['id']}", json={"lost_reason_code": "vadret"}))
        assert falten == [{"field": "lost_reason_code", "code": "forlustorsak_okand"}]


async def test_tidslinjens_avslutade_affar_bar_koden(buddy):
    async with buddy.klient() as k:
        bolag = (await k.post(f"{V1}/companies", json={"name": "Kund AB"})).json()
        forlorad = (await _steg(k))["Förlorad"]
        await k.post(f"{V1}/deals", json={"name": "Växel", "company_id": bolag["id"], "stage_id": forlorad["id"],
                                          "lost_reason_code": "no_budget"})
        linje = (await k.get(f"{V1}/companies/{bolag['id']}/timeline")).json()["data"]
    slut = next(p for p in linje if p["type"] == "deal_closed")
    assert slut["data"]["lost_reason_code"] == "no_budget"


async def test_tomd_affar_tappar_koden(buddy, storage):
    async with buddy.klient() as k:
        affar = (await k.post(f"{V1}/deals", json={"name": "Växel", "lost_reason_code": "timing"})).json()
        assert (await k.delete(f"{V1}/deals/{affar['id']}", params={"permanent": "true"})).status_code == 204
    rad = await lagring.hamta_post(storage, buddy.id, "affar", affar["id"], med_raderade=True)
    assert rad["forlustorsak_kod"] is None


# -- 3. Källa och insamlingsdag på personen ----------------------------------


async def test_person_genom_api_far_insamlingsdag_men_ingen_gissad_kalla(buddy, annan, storage):
    async with buddy.klient() as k:
        utan = (await k.post(f"{V1}/people", json={"first_name": "Anna", "email": "anna@kund.se"})).json()
        assert utan["source_type"] is None and utan["source_name"] is None and utan["collected_at"]
        assert utan["source"] == "api"
        med = (await k.post(f"{V1}/people", json={
            "first_name": "Bo", "email": "bo@kund.se", "source_type": "company_website",
            "source_name": "https://kund.se/om-oss", "collected_at": "2026-11-01T10:00:00+01:00"})).json()
        assert med["source_type"] == "company_website" and med["source_name"] == "https://kund.se/om-oss"
        assert med["collected_at"].startswith("2026-11-01")
        rad = await lagring.hamta_post(storage, buddy.id, "person", med["id"])
        assert rad["kalla_typ"] == "bolagets_webbplats" and rad["kalla"] == "api"
        # Filtren.
        webb = (await k.get(f"{V1}/people", params={"source_type": "company_website"})).json()["data"]
        assert [p["id"] for p in webb] == [med["id"]]
        saknar = (await k.get(f"{V1}/people", params={"missing_source": "true"})).json()["data"]
        assert [p["id"] for p in saknar] == [utan["id"]]
        assert (await k.get(f"{V1}/people", params={"source_type": "gissning"})).status_code == 422
        # Källan sätts i efterhand och syns i historiken med API:ts namn.
        andrad = (await k.patch(f"{V1}/people/{utan['id']}", json={"source_type": "customer_provided"})).json()
        assert andrad["source_type"] == "customer_provided"
        historik = (await k.get(f"{V1}/people/{utan['id']}/history")).json()["data"]
        assert historik[0]["fields"] == ["source_type"]
        assert (await k.get(f"{V1}/people", params={"missing_source": "true"})).json()["data"] == []
    async with annan.klient() as k:
        assert (await k.get(f"{V1}/people", params={"source_type": "company_website"})).json()["data"] == []
        assert (await k.get(f"{V1}/people", params={"missing_source": "true"})).json()["data"] == []


async def test_okand_kalltyp_avvisas(buddy):
    async with buddy.klient() as k:
        falten = _faltfel(await k.post(f"{V1}/people", json={"email": "a@kund.se", "source_type": "rykten"}))
        assert falten == [{"field": "source_type", "code": "kalltyp_okand"}]
        person = (await k.post(f"{V1}/people", json={"email": "a@kund.se"})).json()
        falten = _faltfel(await k.patch(f"{V1}/people/{person['id']}", json={"source_type": "rykten"}))
        assert falten == [{"field": "source_type", "code": "kalltyp_okand"}]


async def test_synken_satter_kallan_och_skriver_aldrig_over_den(buddy, storage):
    async with buddy.klient() as k:
        svar = await k.post(f"{V1}/connections", json={
            "name": "lime", "system": "generisk",
            "mapping": {"person": {"kalla_typ": "kalltyp", "kalla_namn": "kallnamn"}}})
        assert svar.status_code == 201, svar.text
        # Utan uppgift från källan: synk, anslutningens namn och i dag.
        forsta = (await k.post(f"{V1}/sync/people", json={"connection": "lime", "items": [
            {"id": "p1", "email": "anna@kund.se", "first_name": "Anna"},
            {"id": "p2", "email": "bo@kund.se", "kalltyp": "register", "kallnamn": "Bolagsverket"}]})).json()
        anna_id, bo_id = forsta["items"][0]["id"], forsta["items"][1]["id"]
        anna = (await k.get(f"{V1}/people/{anna_id}")).json()
        assert anna["source_type"] == "sync" and anna["source_name"] == "lime" and anna["collected_at"]
        bo = (await k.get(f"{V1}/people/{bo_id}")).json()
        assert bo["source_type"] == "registry" and bo["source_name"] == "Bolagsverket" and bo["collected_at"]
        # En senare synk med en annan källa skriver inte över, men ändrar annat.
        andra = (await k.post(f"{V1}/sync/people", json={"connection": "lime", "items": [
            {"id": "p1", "email": "anna@kund.se", "first_name": "Annie", "kalltyp": "kunden", "kallnamn": "Mässan"},
            {"id": "p2", "email": "bo@kund.se", "kalltyp": "annan", "kallnamn": "Någon"}]})).json()
        assert [p["status"] for p in andra["items"]] == ["updated", "unchanged"]
        anna_efter = (await k.get(f"{V1}/people/{anna_id}")).json()
        assert anna_efter["first_name"] == "Annie"
        assert (anna_efter["source_type"], anna_efter["source_name"], anna_efter["collected_at"]) == (
            "sync", "lime", anna["collected_at"])
        bo_efter = (await k.get(f"{V1}/people/{bo_id}")).json()
        assert (bo_efter["source_type"], bo_efter["source_name"]) == ("registry", "Bolagsverket")
        # En person utan källa (skapad i appen) får källan fylld av synken.
        utan = (await k.post(f"{V1}/people", json={"email": "cecilia@kund.se"})).json()
        await k.post(f"{V1}/sync/people", json={"connection": "lime", "items": [
            {"id": "p3", "email": "cecilia@kund.se", "kalltyp": "bolagets_webbplats", "kallnamn": "kund.se"}]})
        cecilia = (await k.get(f"{V1}/people/{utan['id']}")).json()
        assert (cecilia["source_type"], cecilia["source_name"]) == ("company_website", "kund.se")
        assert cecilia["collected_at"] == utan["collected_at"]


async def test_okand_kalltyp_i_synken_tappar_faltet_inte_posten(buddy):
    async with buddy.klient() as k:
        await k.post(f"{V1}/connections", json={"name": "lime", "system": "generisk",
                                                "mapping": {"person": {"kalla_typ": "kalltyp"}}})
        svar = (await k.post(f"{V1}/sync/people", json={"connection": "lime", "items": [
            {"id": "p1", "email": "anna@kund.se", "kalltyp": "rykten"}]})).json()
        post = svar["items"][0]
        assert post["status"] == "created"
        assert post["field_errors"][0]["falt"] == "kalla_typ" and post["field_errors"][0]["kod"] == "kalltyp_okand"
        # Utan giltig uppgift från källan blir källan synken.
        assert (await k.get(f"{V1}/people/{post['id']}")).json()["source_type"] == "sync"


async def test_gravstenen_nollar_kallan(buddy, storage):
    async with buddy.klient() as k:
        person = (await k.post(f"{V1}/people", json={"email": "anna@kund.se", "source_type": "registry",
                                                     "source_name": "Bolagsverket"})).json()
        assert (await k.delete(f"{V1}/people/{person['id']}", params={"permanent": "true"})).status_code == 204
    rad = await lagring.hamta_post(storage, buddy.id, "person", person["id"], med_raderade=True)
    assert rad["kalla"] == lagring.GRAVSTEN
    assert rad["kalla_typ"] is None and rad["kalla_namn"] is None and rad["insamlad_at"] is None
