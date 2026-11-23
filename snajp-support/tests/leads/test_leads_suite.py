"""Leads Suite (plan del F, Fas 10): statuslogg, tidslinje, anteckningar,
uppgifter, sparade vyer, CSV-import och envägssynken till externt CRM.

API:t prövas över HTTP mot appen i minne (MemoryStorage), CRM-synken med
httpx.MockTransport vid nätverksgränsen."""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.integrationer import lagring as integrationer
from app.leads import crm_synk
from app.main import app
from app.storage.memory import MemoryStorage

DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}
TENANT = "00000000-0000-4000-a000-000000000001"
ANNAN = "00000000-0000-4000-a000-0000000000ff"

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _prospekt(namn: str = "Alfa Bygg AB") -> dict:
    return await app.state.storage.create_prospect(TENANT, company_name=namn, origin="manual")


# -- Statusloggen ---------------------------------------------------------------


async def test_statusbyte_loggas_och_syns_i_tidslinjen():
    async with app.router.lifespan_context(app):
        p = await _prospekt()
        async with _client() as client:
            svar = await client.patch(f"/api/leads/prospects/{p['id']}", headers=DEMO, json={"status": "contacted"})
            assert svar.status_code == 200, svar.text
            # Samma status igen är inget byte och loggas inte.
            await client.patch(f"/api/leads/prospects/{p['id']}", headers=DEMO, json={"status": "contacted"})

            logg = await app.state.storage.list_status_logg(TENANT, prospect_id=p["id"])
            assert [(r["fran"], r["till"], r["kalla"]) for r in logg] == [("new", "contacted", "manuell")]

            linje = (await client.get(f"/api/leads/prospects/{p['id']}/tidslinje", headers=DEMO)).json()["handelser"]
            assert [h["typ"] for h in linje] == ["status", "skapad"]
            assert linje[0]["rubrik"] == "new → contacted"

            lista = (await client.get("/api/leads/prospects", headers=DEMO)).json()["prospects"]
            rad = next(x for x in lista if x["id"] == p["id"])
            assert rad["senaste_handelse_at"] == logg[0]["created_at"]


async def test_kodens_statusbyte_far_kalla_kod():
    storage = MemoryStorage()
    p = await storage.create_prospect(TENANT, company_name="Beta AB")
    await storage.update_prospect(TENANT, p["id"], status="replied")
    [rad] = await storage.list_status_logg(TENANT)
    assert rad["kalla"] == "kod" and rad["till"] == "replied"


# -- Anteckningar, uppgifter, tidslinje ----------------------------------------


async def test_anteckning_och_uppgift_syns_nyast_forst():
    async with app.router.lifespan_context(app):
        p = await _prospekt("Gamma AB")
        async with _client() as client:
            a = await client.post(f"/api/leads/prospects/{p['id']}/anteckningar", headers=DEMO, json={"text": "Ringde VD"})
            assert a.status_code == 201, a.text
            await asyncio.sleep(0.002)
            u = await client.post(
                f"/api/leads/prospects/{p['id']}/uppgifter",
                headers=DEMO,
                json={"titel": "Skicka offert", "forfaller": "2026-10-09"},
            )
            assert u.status_code == 201, u.text
            assert u.json()["uppgift"]["forfaller"] == "2026-10-09"

            linje = (await client.get(f"/api/leads/prospects/{p['id']}/tidslinje", headers=DEMO)).json()["handelser"]
            assert [h["typ"] for h in linje] == ["uppgift", "anteckning", "skapad"]
            assert linje[0]["rubrik"] == "Skicka offert" and linje[0]["klar"] is False
            assert linje[1]["text"] == "Ringde VD"

            tom = await client.post(f"/api/leads/prospects/{p['id']}/anteckningar", headers=DEMO, json={"text": ""})
            assert tom.status_code == 422
            okand = await client.get("/api/leads/prospects/inte-ett-uuid/tidslinje", headers=DEMO)
            assert okand.status_code == 404


async def test_uppgift_klar_satter_klar_at_och_filtreras():
    async with app.router.lifespan_context(app):
        p = await _prospekt("Delta AB")
        async with _client() as client:
            u = (await client.post(
                f"/api/leads/prospects/{p['id']}/uppgifter", headers=DEMO, json={"titel": "Följ upp", "forfaller": None}
            )).json()["uppgift"]
            assert u["klar"] is False and u["klar_at"] is None

            klar = await client.patch(f"/api/leads/uppgifter/{u['id']}", headers=DEMO, json={"klar": True})
            assert klar.status_code == 200, klar.text
            assert klar.json()["uppgift"]["klar"] is True and klar.json()["uppgift"]["klar_at"]

            oppna = (await client.get("/api/leads/uppgifter?oppna=1", headers=DEMO)).json()["uppgifter"]
            assert u["id"] not in [x["id"] for x in oppna]
            alla = (await client.get("/api/leads/uppgifter", headers=DEMO)).json()["uppgifter"]
            assert u["id"] in [x["id"] for x in alla]

            saknas = await client.patch(
                "/api/leads/uppgifter/00000000-0000-4000-a000-00000000abcd", headers=DEMO, json={"klar": True}
            )
            assert saknas.status_code == 404


async def test_mejl_i_tidslinjen():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        p = await _prospekt("Epsilon AB")
        trad = await storage.ensure_outreach_thread(TENANT, prospect_id=p["id"])
        ut = await storage.queue_outreach_message(
            TENANT, thread_id=trad["id"], body="Hej " + "x" * 400, subject="Förslag",
            humanizer_variant="a", scheduled_at=None,
        )
        await storage.mark_outreach_message_sent(TENANT, ut["message"]["id"], "2026-10-01T09:00:00+00:00")
        await storage.record_inbound_reply(TENANT, thread_id=trad["id"], body="Låter bra")
        async with _client() as client:
            linje = (await client.get(f"/api/leads/prospects/{p['id']}/tidslinje", headers=DEMO)).json()["handelser"]
        typer = [h["typ"] for h in linje]
        assert typer.index("mejl_in") < typer.index("mejl_ut")
        mejl_ut = next(h for h in linje if h["typ"] == "mejl_ut")
        assert mejl_ut["rubrik"] == "Förslag" and len(mejl_ut["text"]) == 300


# -- Sparade vyer --------------------------------------------------------------


async def test_vyer_skapas_listas_och_raderas():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            ny = await client.post("/api/leads/vyer", headers=DEMO, json={"namn": "Heta", "filter": {"niva": ["A"]}})
            assert ny.status_code == 201, ny.text
            vy = ny.json()["vy"]
            assert set(vy) == {"id", "namn", "filter", "created_at"} and vy["filter"] == {"niva": ["A"]}

            vyer = (await client.get("/api/leads/vyer", headers=DEMO)).json()["vyer"]
            assert vy["id"] in [v["id"] for v in vyer]

            # En annan tenants vy går inte att radera härifrån.
            frammande = await app.state.storage.create_lead_view(ANNAN, namn="Deras", filter={})
            assert (await client.delete(f"/api/leads/vyer/{frammande['id']}", headers=DEMO)).status_code == 404
            assert await app.state.storage.list_lead_views(ANNAN)

            assert (await client.delete(f"/api/leads/vyer/{vy['id']}", headers=DEMO)).status_code == 204
            assert (await client.delete(f"/api/leads/vyer/{vy['id']}", headers=DEMO)).status_code == 404


# -- Import --------------------------------------------------------------------


async def test_import_skapar_lista_med_kalla_import():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            svar = await client.post(
                "/api/leads/import",
                headers=DEMO,
                json={
                    "titel": "Från HubSpot",
                    "rader": [
                        {"company_name": "Zeta AB", "contact_email": "vd@zeta.se", "contact_phone": "070-1", "status": "Lead"},
                        {"company_name": "Eta AB", "orgnr": "556000-0003", "website": "eta.se"},
                        {"company_name": "  ", "contact_name": "Utan bolag"},
                        {"contact_email": "x@y.se"},
                    ],
                },
            )
            assert svar.status_code == 201, svar.text
            body = svar.json()
            assert body["antal"] == 2 and body["hoppade_over"] == 2
            assert body["list"]["kalla"] == "import" and body["list"]["status"] == "klar"

            detalj = (await client.get(f"/api/leads/listor/{body['list']['id']}", headers=DEMO)).json()
            assert [r["company_name"] for r in detalj["items"]] == ["Zeta AB", "Eta AB"]
            assert detalj["items"][0]["contact_phone"] == "070-1"

            tom = await client.post("/api/leads/import", headers=DEMO, json={"titel": "Tom", "rader": [{"orgnr": "1"}]})
            assert tom.status_code == 422


async def _importera(client, **json_) -> httpx.Response:
    json_.setdefault("titel", "Import")
    return await client.post("/api/leads/import", headers=DEMO, json=json_)


async def _crm_kund(client, namn: str, orgnr: str | None = None) -> None:
    svar = await _importera(client, titel="Kunder", kalla="crm", rader=[{"company_name": namn, "orgnr": orgnr}])
    assert svar.status_code == 201, svar.text


async def test_import_hoppar_over_och_raknar_varje_skal():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        await _prospekt("Leadbolaget AB")
        await storage.add_suppression(TENANT, email="Nej@Sparr.se", reason="test")
        async with _client() as client:
            await _crm_kund(client, "Kundbolaget AB", "556000-1111")
            svar = await _importera(
                client,
                rader=[
                    {"company_name": "Nytt Bolag AB"},
                    {"company_name": " ", "contact_email": "a@b.se"},
                    {"company_name": "nytt bolag"},  # samma bolag utan bolagsform
                    {"company_name": "Annat namn", "orgnr": "5560001111"},  # kund på orgnr
                    {"company_name": "Spärrbolaget AB", "contact_email": "nej@sparr.se"},
                    {"company_name": "Leadbolaget"},
                ],
            )
            assert svar.status_code == 201, svar.text
            body = svar.json()
            assert body["antal"] == 1 and body["hoppade_over"] == 5
            assert body["hoppade"] == {
                "utan_bolag": 1, "dubbletter": 1, "redan_kund": 1, "redan_lead": 1, "sparrade": 1,
            }
            assert body["list"]["item_count"] == 1 and body["list"]["status"] == "klar"


async def test_import_skalens_foretrade():
    """Kund före spärrad före lead före dubblett."""
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        await _prospekt("Bada AB")
        await _prospekt("Leaddubbel AB")
        await storage.add_suppression(TENANT, email="s@x.se", reason="test")
        async with _client() as client:
            await _crm_kund(client, "Bada AB")
            svar = await _importera(
                client,
                rader=[
                    {"company_name": "Bada AB", "contact_email": "s@x.se"},  # kund + spärr + lead
                    {"company_name": "Leaddubbel AB", "contact_email": "s@x.se"},  # spärr + lead
                    {"company_name": "Leaddubbel AB"},  # lead (och dubblett i filen)
                    {"company_name": "Först AB"},
                ],
            )
            body = svar.json()
            assert body["hoppade"] == {
                "utan_bolag": 0, "dubbletter": 0, "redan_kund": 1, "redan_lead": 1, "sparrade": 1,
            }
            assert body["antal"] == 1

            # Lead före dubblett: bolaget står redan i målistan OCH i en annan lista.
            mal = (await _importera(client, titel="Mål", rader=[{"company_name": "Tvåställe AB"}])).json()["list"]["id"]
            await _importera(client, titel="Annan", ta_med_leads=True, rader=[{"company_name": "Tvåställe AB"}])
            pafyllt = await _importera(client, list_id=mal, rader=[{"company_name": "Tvåställe AB"}])
            assert pafyllt.json()["hoppade"]["redan_lead"] == 1 and pafyllt.json()["hoppade"]["dubbletter"] == 0
            med = await _importera(client, list_id=mal, ta_med_leads=True, rader=[{"company_name": "Tvåställe AB"}])
            assert med.json()["hoppade"]["dubbletter"] == 1


async def test_import_ta_med_leads_tar_med_men_aldrig_kunder_eller_sparrade():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        await _prospekt("Leadett AB")
        await storage.add_suppression(TENANT, email="s@x.se", reason="test")
        async with _client() as client:
            await _crm_kund(client, "Kundett AB")
            # Ett bolag i en annan (vanlig) lista är också ett lead.
            assert (await _importera(client, titel="Förra", rader=[{"company_name": "Listbolag AB"}])).status_code == 201
            svar = await _importera(
                client,
                ta_med_leads=True,
                rader=[
                    {"company_name": "Leadett AB"},
                    {"company_name": "Listbolag AB"},
                    {"company_name": "Kundett AB"},
                    {"company_name": "Spärrat AB", "contact_email": "s@x.se"},
                ],
            )
            body = svar.json()
            assert body["antal"] == 2
            assert body["hoppade"]["redan_kund"] == 1 and body["hoppade"]["sparrade"] == 1
            assert body["hoppade"]["redan_lead"] == 0

            utan = await _importera(client, titel="Utan", rader=[{"company_name": "Listbolag AB"}, {"company_name": "Ny AB"}])
            assert utan.json()["hoppade"]["redan_lead"] == 1 and utan.json()["antal"] == 1


async def test_crm_import_hoppar_bara_over_utan_bolag_och_dubbletter():
    async with app.router.lifespan_context(app):
        await _prospekt("Crmlead AB")
        async with _client() as client:
            await _crm_kund(client, "Gammal Kund AB")
            svar = await _importera(
                client,
                kalla="crm",
                rader=[
                    {"company_name": "Crmlead AB"},
                    {"company_name": "Gammal Kund AB"},
                    {"company_name": "Crmlead"},
                    {"company_name": ""},
                ],
            )
            body = svar.json()
            assert body["antal"] == 2
            assert body["hoppade"] == {
                "utan_bolag": 1, "dubbletter": 1, "redan_kund": 0, "redan_lead": 0, "sparrade": 0,
            }


async def test_import_i_delar_med_list_id():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            forsta = await _importera(
                client, titel="Stor fil", importinfo={"fil": "a.csv", "del": 1},
                rader=[{"company_name": "Del Ett AB"}, {"company_name": "Del Två AB"}],
            )
            assert forsta.status_code == 201, forsta.text
            lid = forsta.json()["list"]["id"]
            assert forsta.json()["list"]["importinfo"] == {"fil": "a.csv", "del": 1}

            andra = await client.post(
                "/api/leads/import", headers=DEMO,
                json={
                    "list_id": lid, "importinfo": {"fil": "a.csv", "del": 2},
                    "rader": [{"company_name": "Del Ett"}, {"company_name": "Del Tre AB"}],
                },
            )
            assert andra.status_code == 201, andra.text
            body = andra.json()
            # Raden som redan står i listan är en dubblett, inte ett lead.
            assert body["antal"] == 1 and body["hoppade"]["dubbletter"] == 1 and body["hoppade"]["redan_lead"] == 0
            assert body["list"]["id"] == lid and body["list"]["item_count"] == 3
            assert body["list"]["importinfo"] == {"fil": "a.csv", "del": 2}

            # Alla överhoppade i en fortsättning är inget fel.
            tom = await client.post(
                "/api/leads/import", headers=DEMO, json={"list_id": lid, "rader": [{"company_name": "Del Tre"}]}
            )
            assert tom.status_code == 201 and tom.json()["antal"] == 0
            assert tom.json()["list"]["importinfo"] == {"fil": "a.csv", "del": 2}

            listor = (await client.get("/api/leads/listor", headers=DEMO)).json()["lists"]
            rad = next(x for x in listor if x["id"] == lid)
            assert rad["importinfo"] == {"fil": "a.csv", "del": 2} and rad["item_count"] == 3


async def test_import_list_id_fel():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        async with _client() as client:
            saknas = await _importera(client, list_id="00000000-0000-4000-a000-00000000abcd", rader=[{"company_name": "X AB"}])
            assert saknas.status_code == 404
            assert (await _importera(client, list_id="inte-ett-uuid", rader=[{"company_name": "X AB"}])).status_code == 404

            # En annan kunds lista finns inte här.
            deras = await storage.create_lead_list(ANNAN, titel="Deras", icp={}, antal=1, kalla="import")
            frammande = await _importera(client, list_id=deras["id"], rader=[{"company_name": "X AB"}])
            assert frammande.status_code == 404
            assert await storage.list_lead_list_items(ANNAN, deras["id"]) == []

            crm = (await _importera(client, kalla="crm", rader=[{"company_name": "Kund AB"}])).json()["list"]["id"]
            fel_slag = await _importera(client, list_id=crm, rader=[{"company_name": "X AB"}])
            assert fel_slag.status_code == 409
            sokt = await storage.create_lead_list(TENANT, titel="Sökt", icp={}, antal=1, kalla="sok")
            assert (await _importera(client, list_id=sokt["id"], rader=[{"company_name": "X AB"}])).status_code == 409

            utan_titel = await client.post("/api/leads/import", headers=DEMO, json={"rader": [{"company_name": "X AB"}]})
            assert utan_titel.status_code == 422


async def test_import_tak_5000_rader_per_lista():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            forsta = await _importera(client, rader=[{"company_name": f"Takbolag {i}"} for i in range(4999)])
            assert forsta.status_code == 201, forsta.text
            lid = forsta.json()["list"]["id"]
            over = await _importera(client, list_id=lid, rader=[{"company_name": "Tak A"}, {"company_name": "Tak B"}])
            assert over.status_code == 422 and over.json()["detail"] == "Högst 5 000 rader per lista."
            assert len(await app.state.storage.list_lead_list_items(TENANT, lid)) == 4999
            precis = await _importera(client, list_id=lid, rader=[{"company_name": "Tak A"}])
            assert precis.status_code == 201 and precis.json()["list"]["item_count"] == 5000


async def test_import_avtalsslut_extra_och_ort_syns_i_listan():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            extra = {f"kolumn {i}": f"v{i}" for i in range(45)}
            extra["kolumn 0"] = "x" * 600
            extra["r" * 150] = "lång rubrik"
            svar = await _importera(
                client,
                rader=[
                    {"company_name": "Avtal AB", "ort": "Umeå", "avtalsslut": "2027-03-31", "extra": extra},
                    {"company_name": "Trasigt AB", "avtalsslut": "31/3 nästa år", "extra": {"Tom": "", "Siffra": 7}},
                    {"company_name": "Ogiltigt AB", "avtalsslut": "2027-02-30"},
                ],
            )
            assert svar.status_code == 201, svar.text
            items = (await client.get(f"/api/leads/listor/{svar.json()['list']['id']}", headers=DEMO)).json()["items"]
            a, b, c = items
            assert a["avtalsslut"] == "2027-03-31" and a["ort"] == "Umeå"
            assert len(a["extra"]) == 40 and len(a["extra"]["kolumn 0"]) == 500
            assert "r" * 150 not in a["extra"]
            assert b["avtalsslut"] is None and b["extra"] == {"Siffra": "7"}
            assert c["avtalsslut"] is None and c["extra"] is None


async def test_import_kvittot_for_stort():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            svar = await _importera(client, importinfo={"x": "y" * 21_000}, rader=[{"company_name": "Kvitto AB"}])
            assert svar.status_code == 422
            assert not [x for x in (await client.get("/api/leads/listor", headers=DEMO)).json()["lists"]
                        if x["titel"] == "Import"]


async def test_import_alla_overhoppade_ger_422_med_skalen():
    async with app.router.lifespan_context(app):
        await _prospekt("Redan AB")
        async with _client() as client:
            svar = await _importera(client, rader=[{"company_name": "Redan AB"}, {"company_name": ""}])
            assert svar.status_code == 422
            detalj = svar.json()["detail"]
            assert "1 utan bolagsnamn" in detalj and "1 redan leads" in detalj


async def test_granska_flaggar_i_ordning_och_skriver_inget():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        await _prospekt("Granskalead AB")
        await _prospekt("Granskakund AB")
        await storage.add_suppression(TENANT, email="s@x.se", reason="test")
        async with _client() as client:
            await _crm_kund(client, "Granskakund AB")
            listor_fore = await storage.list_lead_lists(TENANT)
            prospekt_fore = await storage.list_prospects(TENANT, limit=20_000)
            rader = [
                {"company_name": "Granskakund AB", "contact_email": "s@x.se"},
                {"company_name": "Granskalead AB", "contact_email": "s@x.se"},
                {"company_name": "Granskalead"},
                {"company_name": "Helt Nytt AB"},
            ]
            svar = await client.post("/api/leads/import/granska", headers=DEMO, json={"kalla": "import", "rader": rader})
            assert svar.status_code == 200, svar.text
            assert svar.json() == {
                "flaggor": ["kund", "sparrad", "lead", None],
                "antal": {"kund": 1, "sparrad": 1, "lead": 1},
            }
            crm = await client.post("/api/leads/import/granska", headers=DEMO, json={"kalla": "crm", "rader": rader})
            assert crm.json()["flaggor"] == [None] * 4

            assert await storage.list_lead_lists(TENANT) == listor_fore
            assert await storage.list_prospects(TENANT, limit=20_000) == prospekt_fore
            tom = await client.post("/api/leads/import/granska", headers=DEMO, json={"rader": []})
            assert tom.status_code == 422


async def test_import_och_granska_sparrar_adress_med_begransad_behandling():
    """GDPR art. 18 (migration 124): en adress med begränsad behandling lagras
    inte på nytt. Listan är global, så raden tas bort igen efter testet."""
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        begransning = {"email": "Art18@Begransad.se", "havd_at": None}
        storage.behandlingsbegransningar.append(begransning)
        try:
            async with _client() as client:
                rader = [
                    {"company_name": "Begränsad AB", "contact_email": "art18@begransad.se"},
                    {"company_name": "Fri Väg AB", "contact_email": "ok@frivag.se"},
                ]
                granska = await client.post("/api/leads/import/granska", headers=DEMO, json={"kalla": "import", "rader": rader})
                assert granska.json()["flaggor"] == ["sparrad", None]
                svar = await _importera(client, titel="Art 18", rader=rader)
                assert svar.status_code == 201, svar.text
                assert svar.json()["antal"] == 1 and svar.json()["hoppade"]["sparrade"] == 1
        finally:
            storage.behandlingsbegransningar.remove(begransning)


async def test_kombinera_behaller_avtalsslut_och_extra():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            lid = (await _importera(
                client, rader=[{"company_name": "Kombo AB", "avtalsslut": "2026-12-01", "extra": {"Segment": "A"}}]
            )).json()["list"]["id"]
            lid2 = (await _importera(client, titel="Andra", rader=[{"company_name": "Kombo Två AB"}])).json()["list"]["id"]
            svar = await client.post(
                "/api/leads/listor/kombinera", headers=DEMO,
                json={"titel": "Kombo", "list_ids": [lid, lid2], "kontaktfilter": "alla"},
            )
            assert svar.status_code == 201, svar.text
            rad, andra = svar.json()["items"]
            assert rad["avtalsslut"] == "2026-12-01" and rad["extra"] == {"Segment": "A"}
            assert andra["avtalsslut"] is None and andra["extra"] is None


# -- Automationsinställningarna i config ---------------------------------------


async def test_config_automation_faltvis_och_crm_synk():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            start = (await client.get("/api/leads/config", headers=DEMO)).json()
            assert start["automation"]["per_typ"]["inkorg"]["utkast_auto"] is False
            assert start["crm_synk"] == {"leverantor": None, "integration_id": None}

            await client.put(
                "/api/leads/config", headers=DEMO,
                json={"automation": {"per_typ": {"import": {"uppfoljning_dagar": 0}}}},
            )
            svar = await client.put(
                "/api/leads/config", headers=DEMO,
                json={"automation": {"per_typ": {"import": {"utkast_auto": False}}, "jev_bortval": False}},
            )
            assert svar.status_code == 200, svar.text
            regler = svar.json()["automation"]
            assert regler["per_typ"]["import"] == {"utkast_auto": False, "uppfoljning_dagar": 0}
            assert regler["jev_bortval"] is False

            fel = await client.put("/api/leads/config", headers=DEMO, json={"automation": {"per_typ": {"iris": {"uppfoljning_dagar": 61}}}})
            assert fel.status_code == 422
            okand = await client.put(
                "/api/leads/config", headers=DEMO,
                json={"crm_synk": {"leverantor": "hubspot", "integration_id": "00000000-0000-4000-a000-00000000beef"}},
            )
            assert okand.status_code == 422


# -- CRM-synken ----------------------------------------------------------------


async def _med_crm(storage, leverantor: str) -> None:
    rad = await integrationer.skapa(
        storage, TENANT, typ="http", namn=f"CRM {leverantor}", beskrivning="",
        konfig={}, hemligheter={"api_key": "hemlig-nyckel"},
    )
    await storage.set_agent_settings(
        TENANT, agent_type="leads", settings={"crm_synk": {"leverantor": leverantor, "integration_id": rad["id"]}}
    )


def _mocka(monkeypatch, handler) -> list[httpx.Request]:
    anrop: list[httpx.Request] = []
    original = httpx.AsyncClient

    def _hanterare(request: httpx.Request) -> httpx.Response:
        anrop.append(request)
        return handler(request)

    monkeypatch.setattr(
        crm_synk.httpx, "AsyncClient", lambda **kw: original(transport=httpx.MockTransport(_hanterare), **kw)
    )
    return anrop


async def test_hubspot_skapar_bolag_och_anteckning(monkeypatch):
    storage = MemoryStorage()
    await _med_crm(storage, "hubspot")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer hemlig-nyckel"
        if request.url.path.endswith("/companies/search"):
            return httpx.Response(200, json={"results": []})
        if request.url.path.endswith("/objects/companies"):
            return httpx.Response(201, json={"id": "42"})
        return httpx.Response(201, json={"id": "n1"})

    anrop = _mocka(monkeypatch, handler)
    prospect = {"id": "p", "company_name": "Theta AB", "website": "https://www.theta.se/om", "contact_phone": "08-1"}
    await crm_synk.synka_prospekt(storage, TENANT, prospect, handelse="status", text="contacted")

    assert [(r.method, r.url.path) for r in anrop] == [
        ("POST", "/crm/v3/objects/companies/search"),
        ("POST", "/crm/v3/objects/companies"),
        ("POST", "/crm/v3/objects/notes"),
    ]
    bolag = json.loads(anrop[1].content)["properties"]
    assert bolag == {"name": "Theta AB", "domain": "theta.se", "phone": "08-1"}
    notis = json.loads(anrop[2].content)
    assert notis["properties"]["hs_note_body"] == "Snipra: status: contacted"
    assert notis["associations"][0]["to"]["id"] == "42"
    assert notis["associations"][0]["types"][0]["associationTypeId"] == 190


async def test_pipedrive_uppdaterar_befintlig_organisation(monkeypatch):
    storage = MemoryStorage()
    await _med_crm(storage, "pipedrive")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["api_token"] == "hemlig-nyckel"
        if request.url.path.endswith("/organizations/search"):
            return httpx.Response(200, json={"data": {"items": [{"item": {"id": 7}}]}})
        if request.method == "PUT":
            return httpx.Response(200, json={"data": {"id": 7}})
        return httpx.Response(201, json={"data": {"id": 99}})

    anrop = _mocka(monkeypatch, handler)
    await crm_synk.synka_prospekt(
        storage, TENANT, {"id": "p", "company_name": "Iota AB"}, handelse="anteckning", text="Ringde"
    )
    assert [(r.method, r.url.path) for r in anrop] == [
        ("GET", "/v1/organizations/search"),
        ("PUT", "/v1/organizations/7"),
        ("POST", "/v1/notes"),
    ]
    assert json.loads(anrop[2].content) == {"content": "Snipra: anteckning: Ringde", "org_id": 7}


async def test_leverantorens_500_kastar_aldrig(monkeypatch):
    storage = MemoryStorage()
    await _med_crm(storage, "hubspot")
    anrop = _mocka(monkeypatch, lambda request: httpx.Response(500, json={"fel": "nere"}))
    await crm_synk.synka_prospekt(storage, TENANT, {"id": "p", "company_name": "Kappa AB"}, handelse="status")
    assert len(anrop) == 1


async def test_utan_installning_gors_inget_anrop(monkeypatch):
    anrop = _mocka(monkeypatch, lambda request: httpx.Response(200, json={}))
    await crm_synk.synka_prospekt(MemoryStorage(), TENANT, {"company_name": "Lambda AB"}, handelse="status")
    assert anrop == []
