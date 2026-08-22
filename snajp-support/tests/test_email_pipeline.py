"""Email-pipelinen: ingest, triage, regler, granskningsflöde och isolation."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import CATEGORIES, get_settings
from app.main import app

settings = get_settings()
DEMO = {"X-API-Key": settings.snajp_demo_api_key}
MASTER = {"X-API-Key": settings.snajp_master_api_key}


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.anyio
async def test_mock_seed_triages_and_creates_drafts():
    """Urvalet roterar, så testet prövar EGENSKAPER och inte enskilda ämnen.

    Det gamla testet läste ut tre bestämda ämnesrader ur inkorgen. Det gick
    bara att skriva så länge "Hämta testmail" gav exakt samma sex mail varje
    gång — vilket var precis felet: kunden fick ingen ny lista när de tryckte
    igen. Kontraktet är numera blandningen, och det är den som testas.

    Antalet är inte heller en siffra i testet längre. Seedningen ger ETT ärende
    per fack, för att en kund som klickar sig runt bland facken annars hittar
    tomma flikar och drar slutsatsen att sorteringen inte fungerar. Ändras
    antalet fack ändras antalet mail, och ett test som pinnat 6 hade fallit av
    fel skäl.
    """
    async with app.router.lifespan_context(app):
        async with _client() as client:
            seeded = await client.post("/api/inbox/mock", headers=DEMO)
            assert seeded.status_code == 201
            assert seeded.json()["ingested"] == len(CATEGORIES)

            emails = (await client.get("/api/inbox", headers=DEMO)).json()["emails"]
            assert len(emails) == len(CATEGORIES)

            # Blandat utfall: minst ett ärende som når en människa, och minst
            # ett där agenten faktiskt skrivit ett svar. En inkorg där allt är
            # eskalerat visar inte en agent som vägrar gissa — den visar en
            # produkt som inte fungerar.
            statusar = {e["status"] for e in emails}
            assert "escalated" in statusar
            assert statusar & {"awaiting_approval", "auto_sent"}

            besvarade = [e for e in emails if e["status"] == "awaiting_approval"]
            assert all(e["draft"]["content"] for e in besvarade)

            # Alla klassificeringar har konfidens + motivering (beslutslogg).
            assert all(e["classification"]["confidence"] > 0 for e in emails)
            assert all(e["classification"]["reasoning"] for e in emails)


@pytest.mark.anyio
async def test_mock_seed_replaces_previous_batch():
    """Andra klicket BYTER UT inkorgen, det fyller inte på den.

    Endpointen lade förut till sex nya mail med nya id:n varje gång. Uppmätt
    följd: listan växte, innehållet var detsamma, och den enda vägen till en
    ren demo var att skapa en ny arbetsyta.
    """
    async with app.router.lifespan_context(app):
        async with _client() as client:
            await client.post("/api/inbox/mock", headers=DEMO)
            forsta = (await client.get("/api/inbox", headers=DEMO)).json()["emails"]

            andra_svar = await client.post("/api/inbox/mock", headers=DEMO)
            assert andra_svar.json()["removed"] == len(forsta)

            andra = (await client.get("/api/inbox", headers=DEMO)).json()["emails"]
            assert len(andra) == len(CATEGORIES)
            assert {e["id"] for e in forsta}.isdisjoint({e["id"] for e in andra})


@pytest.mark.anyio
async def test_email_detail_has_attachments_and_decision_log():
    """Bilagan ingestas explicit i stället för att letas upp i testmailen.

    Ett av mailen i poolen har en skärmdump, men urvalet roterar — att leta
    efter just det mailet hade gett ett test som faller ungefär varannan
    körning. Ingest-vägen ger samma pipeline med känd indata.
    """
    async with app.router.lifespan_context(app):
        async with _client() as client:
            skapad = await client.post(
                "/api/inbox/ingest",
                headers=DEMO,
                json={
                    "from": "anna@example.com",
                    "from_name": "Anna Lindqvist",
                    "subject": "Kan inte logga in på mitt konto",
                    "body": "Får ett felmeddelande vid inloggning. Bifogar skärmdump.",
                    "attachments": [
                        {
                            "filename": "skarmdump-fel.png",
                            "content_type": "image/png",
                            "data_url": (
                                "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAAB"
                                "CAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
                            ),
                        }
                    ],
                },
            )
            assert skapad.status_code == 201

            detail = (
                await client.get(f"/api/inbox/{skapad.json()['email_id']}", headers=DEMO)
            ).json()
            assert detail["attachments"][0]["is_image"] is True
            events = [d["event"] for d in detail["decisions"]]
            assert events[0] == "received"
            assert "classified" in events
            assert "draft_created" in events


@pytest.mark.anyio
async def test_approve_with_edit_sends_and_logs_review():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            await client.post("/api/inbox/mock", headers=DEMO)
            emails = (await client.get("/api/inbox", headers=DEMO)).json()["emails"]
            pending = next(e for e in emails if e["status"] == "awaiting_approval")
            draft_id = pending["draft"]["id"]

            approved = await client.post(
                f"/api/drafts/{draft_id}/approve",
                headers=DEMO,
                json={"edited_content": "Hej! Redigerat svar från människa."},
            )
            assert approved.status_code == 200
            assert approved.json()["edited"] is True

            detail = (await client.get(f"/api/inbox/{pending['id']}", headers=DEMO)).json()
            assert detail["status"] == "sent"
            assert detail["draft"]["status"] == "approved"
            assert "approved_and_sent" in [d["event"] for d in detail["decisions"]]

            # Dubbelgodkännande blockeras.
            again = await client.post(
                f"/api/drafts/{draft_id}/approve", headers=DEMO, json={}
            )
            assert again.status_code == 409


@pytest.mark.anyio
async def test_auto_rule_sends_without_approval():
    """Leveransärendet ingestas explicit — se testet ovan om varför."""
    async with app.router.lifespan_context(app):
        async with _client() as client:
            rule = await client.put(
                "/api/rules", headers=DEMO, json={"category": "leverans", "mode": "auto"}
            )
            assert rule.status_code == 200

            skapad = await client.post(
                "/api/inbox/ingest",
                headers=DEMO,
                json={
                    "from": "johan@example.com",
                    "from_name": "Johan Berg",
                    "subject": "Var är mitt paket?",
                    "body": (
                        "Beställde för en vecka sedan och spårningen har inte "
                        "uppdaterats på fyra dagar. När kommer paketet?"
                    ),
                },
            )
            assert skapad.status_code == 201
            email_id = skapad.json()["email_id"]

            paket = (await client.get(f"/api/inbox/{email_id}", headers=DEMO)).json()
            assert paket["status"] == "auto_sent"
            assert paket["draft"]["auto"] is True
            assert "auto_sent" in [d["event"] for d in paket["decisions"]]


@pytest.mark.anyio
async def test_takeover_and_dedupe():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            first = await client.post(
                "/api/inbox/ingest",
                headers=DEMO,
                json={
                    "from": "kund@example.com",
                    "subject": "Var är paketet",
                    "body": "Min leverans är försenad.",
                    "provider_message_id": "ext-123",
                },
            )
            assert first.status_code == 201
            email_id = first.json()["email_id"]

            duplicate = await client.post(
                "/api/inbox/ingest",
                headers=DEMO,
                json={
                    "from": "kund@example.com",
                    "subject": "Var är paketet",
                    "body": "Min leverans är försenad.",
                    "provider_message_id": "ext-123",
                },
            )
            assert duplicate.status_code == 409

            taken = await client.post(f"/api/inbox/{email_id}/takeover", headers=DEMO)
            assert taken.status_code == 200
            detail = (await client.get(f"/api/inbox/{email_id}", headers=DEMO)).json()
            assert detail["status"] == "taken_over"
            assert detail["draft"]["status"] == "rejected"


@pytest.mark.anyio
async def test_inbox_is_tenant_isolated():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            created = await client.post(
                "/api/keys", headers=MASTER, json={"tenant_name": "Annan Butik AB"}
            )
            key_b = {"X-API-Key": created.json()["api_key"]}

            await client.post("/api/inbox/mock", headers=DEMO)
            inbox_a = (await client.get("/api/inbox", headers=DEMO)).json()["emails"]
            inbox_b = (await client.get("/api/inbox", headers=key_b)).json()["emails"]
            assert len(inbox_a) == len(CATEGORIES)
            assert inbox_b == []

            # Tenant B kan inte läsa eller ta över A:s mail.
            stolen = await client.get(f"/api/inbox/{inbox_a[0]['id']}", headers=key_b)
            assert stolen.status_code == 404
            takeover = await client.post(
                f"/api/inbox/{inbox_a[0]['id']}/takeover", headers=key_b
            )
            assert takeover.status_code == 404
