"""Prospekt-ingången till leads-pipelinen + INV-DATA-002 vid källregistrering."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import DEFAULT_TENANT_ID, get_settings
from app.main import app

DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.anyio
async def test_create_and_list_prospect():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            created = await client.post(
                "/api/leads/prospects",
                headers=DEMO,
                json={"company_name": "Exempelbolaget AB", "contact_email": "info@exempel.se"},
            )
            assert created.status_code == 201
            prospect = created.json()["prospect"]
            assert prospect["status"] == "new"
            assert prospect["language_state"] == "sv"

            listed = await client.get("/api/leads/prospects", headers=DEMO)
            rader = listed.json()["prospects"]
            assert any(p["id"] == prospect["id"] for p in rader)
            # Fas 2 §3, 2.4-backend: origin ska följa med listan utan filter —
            # UI-växeln "Visa testkörningar" (byggs separat) behöver fältet
            # per rad för att kunna filtrera på klientsidan.
            match = next(p for p in rader if p["id"] == prospect["id"])
            assert match["origin"] == "manual"


@pytest.mark.anyio
async def test_is_test_flaggan_ger_origin_test_inte_manual():
    """Fas 2 (plans/2026-08-28 §3): LeadsRunForm.tsx skapar "egna bolag" i en
    testkörning via just den här routen (samma isTest-flagga som går till
    /leads/runs/batch). Utan is_test=true landar raden som origin='manual' —
    omöjlig att skilja från kundens riktiga lista, och oskyddad av
    send-guardens spärr noll. Se test_scheduler.py för att spärren faktiskt
    stoppar den.
    """
    async with app.router.lifespan_context(app):
        async with _client() as client:
            testkorning = await client.post(
                "/api/leads/prospects",
                headers=DEMO,
                json={"company_name": "Provbolaget Test AB"},
                params={"is_test": "true"},
            )
            assert testkorning.status_code == 201
            assert testkorning.json()["prospect"]["origin"] == "test"

            # Standardvägen (ingen flagga alls) ska vara EXAKT som innan —
            # varken en tom flagga eller default-värdet får glida till 'test'.
            riktigt = await client.post(
                "/api/leads/prospects",
                headers=DEMO,
                json={"company_name": "Riktiga Kundbolaget AB"},
            )
            assert riktigt.status_code == 201
            assert riktigt.json()["prospect"]["origin"] == "manual"


@pytest.mark.anyio
async def test_linkedin_cannot_be_the_first_source_inv_data_002():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            prospect = (
                await client.post(
                    "/api/leads/prospects", headers=DEMO, json={"company_name": "LinkedIn-test AB"}
                )
            ).json()["prospect"]

            refused = await client.post(
                f"/api/leads/prospects/{prospect['id']}/sources",
                headers=DEMO,
                json={
                    "source_url": "https://linkedin.com/in/nagon",
                    "source_type": "linkedin",
                    "lawful_basis": "Berättigat intresse",
                },
            )
            assert refused.status_code == 422
            assert "INV-DATA-002" in refused.json()["detail"]


@pytest.mark.anyio
async def test_linkedin_allowed_as_verification_after_another_source():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            prospect = (
                await client.post(
                    "/api/leads/prospects", headers=DEMO, json={"company_name": "Verifierings-AB"}
                )
            ).json()["prospect"]

            first = await client.post(
                f"/api/leads/prospects/{prospect['id']}/sources",
                headers=DEMO,
                json={
                    "source_url": "https://exempel.se",
                    "source_type": "company_website",
                    "lawful_basis": "Publik företagsinformation",
                },
            )
            assert first.status_code == 201

            second = await client.post(
                f"/api/leads/prospects/{prospect['id']}/sources",
                headers=DEMO,
                json={
                    "source_url": "https://linkedin.com/in/nagon",
                    "source_type": "linkedin",
                    "lawful_basis": "Verifiering av befintlig kontakt",
                },
            )
            assert second.status_code == 201


@pytest.mark.anyio
async def test_sources_for_unknown_prospect_returns_404():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            response = await client.post(
                "/api/leads/prospects/00000000-0000-0000-0000-000000000000/sources",
                headers=DEMO,
                json={
                    "source_url": "https://exempel.se",
                    "source_type": "company_website",
                    "lawful_basis": "Publik",
                },
            )
            assert response.status_code == 404


@pytest.mark.anyio
async def test_onboarding_status_endpoint_reports_gaps():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            response = await client.get("/api/leads/onboarding/status", headers=DEMO)
            assert response.status_code == 200
            body = response.json()
            assert set(body["required"]) == {
                "product_marketing",
                "customer_research",
                "retention_playbook",
            }
            assert body["complete"] is False


@pytest.mark.anyio
async def test_runs_endpoint_is_reachable_for_dashboard():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            response = await client.get("/api/leads/runs", headers=DEMO)
            assert response.status_code == 200
            assert "runs" in response.json()


# -- Fas 3 §4: befordra ett testkörnings-/exempelprospekt till 'manual' -----
#
# ProspectRequest (kroppen /api/leads/prospects tar emot) har inget orgnr- eller
# website-fält — de sätts bara via `profil` i exempelbolagsvägen eller av en
# riktig research-körning. Testerna nedan går därför förbi HTTP-lagret och
# skriver prospektet direkt via app.state.storage, precis som andra leads-test
# som behöver ett fält utanför det publika schemat.


@pytest.mark.anyio
async def test_befordra_testkorning_med_giltiga_falt_blir_manual():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        prospekt = await storage.create_prospect(
            DEFAULT_TENANT_ID,
            company_name="Riktiga Byggbolaget AB",
            contact_email="info@riktigabyggbolaget.se",
            origin="test",
            profil={"orgnr": "556824-9022", "website": "https://riktigabyggbolaget.se"},
        )
        async with _client() as client:
            response = await client.post(
                f"/api/leads/prospects/{prospekt['id']}/befordra", headers=DEMO
            )
            assert response.status_code == 200
            body = response.json()
            assert body["andrad"] is True
            assert body["prospect"]["origin"] == "manual"

            # Idempotent: ett andra anrop mot samma (nu redan manuella) prospekt
            # ska INTE falla — se test_befordra_ar_idempotent_for_manual nedan
            # för den fristående kontrollen av just det.


@pytest.mark.anyio
async def test_befordra_exempelbolag_utan_giltigt_orgnr_ger_422_med_faltlista():
    """exempelbolag.py bygger org.nr med flit Luhn-ogiltigt och webbplatsen
    under `.example` (rad ~146–190) — så en 'example'-rad utan att kunden
    fyllt i riktiga uppgifter ska aldrig gå att befordra."""
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        prospekt = await storage.create_prospect(
            DEFAULT_TENANT_ID,
            company_name="Byggkompaniet Syd",
            origin="example",
            profil={"orgnr": "556000-0000", "website": "byggkompanietsyd.example"},
        )
        async with _client() as client:
            response = await client.post(
                f"/api/leads/prospects/{prospekt['id']}/befordra", headers=DEMO
            )
            assert response.status_code == 422
            detail = response.json()["detail"]
            saknas = detail["saknas"]
            # Tre brister: ogiltigt org.nr, .example-domän, ingen kontaktadress.
            assert len(saknas) == 3
            assert any("rganisationsnummer" in rad for rad in saknas)
            assert any("ebbplatsen" in rad for rad in saknas)
            assert any("post" in rad for rad in saknas)
            # Ingen tankstreck i de svenska strängarna kunden ser.
            assert all("—" not in rad and "–" not in rad for rad in saknas)

            # Prospektet ska stå kvar som 'example' — ett avvisat befordran-
            # försök får inte råka ändra origin ändå.
            oforandrat = await storage.get_prospect(DEFAULT_TENANT_ID, prospekt["id"])
            assert oforandrat["origin"] == "example"


@pytest.mark.anyio
async def test_befordra_ar_idempotent_for_manual():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            skapat = await client.post(
                "/api/leads/prospects", headers=DEMO, json={"company_name": "Redan Manuellt AB"}
            )
            prospect = skapat.json()["prospect"]
            assert prospect["origin"] == "manual"

            response = await client.post(
                f"/api/leads/prospects/{prospect['id']}/befordra", headers=DEMO
            )
            assert response.status_code == 200
            body = response.json()
            assert body["andrad"] is False
            assert body["prospect"]["origin"] == "manual"


@pytest.mark.anyio
async def test_befordra_med_ifyllnad_i_kroppen_blir_manual():
    """422-listan ska gå att åtgärda i samma anrop, inte bara som en vägg."""
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        prospekt = await storage.create_prospect(
            DEFAULT_TENANT_ID,
            company_name="Ofullständiga Bygg AB",
            origin="test",
            profil={"orgnr": "556000-0000", "website": "ofullstandiga.example"},
        )
        async with _client() as client:
            avvisat = await client.post(
                f"/api/leads/prospects/{prospekt['id']}/befordra", headers=DEMO
            )
            assert avvisat.status_code == 422

            ifyllt = await client.post(
                f"/api/leads/prospects/{prospekt['id']}/befordra",
                headers=DEMO,
                json={
                    "orgnr": "556824-9022",
                    "website": "https://ofullstandigabygg.se",
                    "contact_email": "info@ofullstandigabygg.se",
                },
            )
            assert ifyllt.status_code == 200
            body = ifyllt.json()
            assert body["andrad"] is True
            assert body["prospect"]["origin"] == "manual"
            assert body["prospect"]["orgnr"] == "556824-9022"


@pytest.mark.anyio
async def test_patch_prospect_skriver_orgnr_webb_och_epost():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            skapat = await client.post(
                "/api/leads/prospects",
                headers=DEMO,
                json={"company_name": "Patchbolaget AB"},
            )
            pid = skapat.json()["prospect"]["id"]
            response = await client.patch(
                f"/api/leads/prospects/{pid}",
                headers=DEMO,
                json={
                    "orgnr": "556824-9022",
                    "website": "https://patchbolaget.se",
                    "contact_email": "hej@patchbolaget.se",
                },
            )
            assert response.status_code == 200
            p = response.json()["prospect"]
            assert p["orgnr"] == "556824-9022"
            assert p["website"] == "https://patchbolaget.se"
            assert p["contact_email"] == "hej@patchbolaget.se"


@pytest.mark.anyio
async def test_befordra_okant_prospekt_ger_404():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            response = await client.post(
                "/api/leads/prospects/00000000-0000-0000-0000-000000000000/befordra",
                headers=DEMO,
            )
            assert response.status_code == 404


# -- Motsatt riktning: degradera ett riktigt prospekt till 'test' ----------
#
# Bolagsregistrets "Flytta"-knapp går åt andra hållet i skarpt läge (se
# components/leads/Bolagsregister.tsx) — och send-guardens spärr noll
# (scheduler.py) måste blockera det degraderade prospektet precis som den
# blockerar ett som föddes som 'test'. Se test_scheduler.py för själva
# spärren; testerna här gäller bara att endpointen sätter rätt origin.


@pytest.mark.anyio
async def test_degradera_manuellt_prospekt_blir_test():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            skapat = await client.post(
                "/api/leads/prospects",
                headers=DEMO,
                json={"company_name": "Flyttas Till Test AB"},
            )
            prospect = skapat.json()["prospect"]
            assert prospect["origin"] == "manual"

            response = await client.post(
                f"/api/leads/prospects/{prospect['id']}/degradera", headers=DEMO
            )
            assert response.status_code == 200
            body = response.json()
            assert body["andrad"] is True
            assert body["prospect"]["origin"] == "test"


@pytest.mark.anyio
async def test_degradera_ar_idempotent_for_test():
    """Ett prospekt som redan är 'test' (eller 'example') ska inte falla —
    samma resonemang som test_befordra_ar_idempotent_for_manual."""
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        prospekt = await storage.create_prospect(
            DEFAULT_TENANT_ID, company_name="Redan Test AB", origin="test"
        )
        async with _client() as client:
            response = await client.post(
                f"/api/leads/prospects/{prospekt['id']}/degradera", headers=DEMO
            )
            assert response.status_code == 200
            body = response.json()
            assert body["andrad"] is False
            assert body["prospect"]["origin"] == "test"


@pytest.mark.anyio
async def test_degradera_okant_prospekt_ger_404():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            response = await client.post(
                "/api/leads/prospects/00000000-0000-0000-0000-000000000000/degradera",
                headers=DEMO,
            )
            assert response.status_code == 404


@pytest.mark.anyio
async def test_senaste_utkast_lasvag_utan_sidoeffekter():
    """Fas 5.5: Bolagssidan ska kunna återfinna ett utkast efter omladdning
    via GET /prospects/{id}/utkast — och en GET på ett prospekt UTAN utkast
    får inte lämna en tom tråd efter sig (find_outreach_thread, inte ensure).
    Meddelande-id:t är kö-id:t: samma id går rakt in i queue/{id}/approve."""
    async with app.router.lifespan_context(app):
        async with _client() as client:
            created = await client.post(
                "/api/leads/prospects",
                headers=DEMO,
                json={"company_name": "Utkastbolaget AB", "contact_email": "vd@utkast.se"},
            )
            pid = created.json()["prospect"]["id"]

            tomt = await client.get(f"/api/leads/prospects/{pid}/utkast", headers=DEMO)
            assert tomt.status_code == 200
            assert tomt.json() == {"utkast": None, "thread_id": None, "queue_item_id": None}

            storage = app.state.storage
            # GET:en ovan får INTE ha skapat tråden.
            assert await storage.find_outreach_thread(DEFAULT_TENANT_ID, prospect_id=pid) is None

            thread = await storage.ensure_outreach_thread(DEFAULT_TENANT_ID, prospect_id=pid)
            skapat = await storage.queue_outreach_message(
                DEFAULT_TENANT_ID,
                thread_id=thread["id"],
                body="Hej, vi hjälper er med kundtjänsten.",
                subject="Snabb fråga",
                humanizer_variant="a",
                scheduled_at=None,
                status="awaiting_review",
            )

            svar = await client.get(f"/api/leads/prospects/{pid}/utkast", headers=DEMO)
            data = svar.json()
            assert data["thread_id"] == thread["id"]
            assert data["utkast"]["id"] == skapat["message"]["id"]
            assert data["utkast"]["subject"] == "Snabb fråga"
            # Kö-id:t är send_queue-radens id — det approve-endpointen tar.
            assert data["queue_item_id"] == skapat["queue_item"]["id"]
