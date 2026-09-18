"""API-ytan för den sömlösa överlämningen och kundens supportregler (bd snipe-1fl).

Medarbetarens sida (/api/chattar), chattfönstrets hämtning (/api/chat/samtal)
och inställningarna (/api/support/config), genom den riktiga appen med
MemoryStorage — samma väg som tests/test_api.py.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import DEFAULT_TENANT_ID, get_settings
from app.main import app

DEMO_KEY = get_settings().snajp_demo_api_key
HEADERS = {"X-API-Key": DEMO_KEY}
SESSION = "11111111-2222-4333-8444-555555555555@session.snajp.se"


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _overlamnat_samtal(storage) -> dict:
    """Ett samtal som agenten lämnat över: kund, ärende, två rader, läge."""
    kund = await storage.find_or_create_customer(
        DEFAULT_TENANT_ID, email=SESSION, phone=None, name="Webbesökare"
    )
    arende = await storage.create_ticket(
        DEFAULT_TENANT_ID, customer_id=kund["id"], subject="Faktura", category="betalning", channel="web"
    )
    await storage.save_message(
        DEFAULT_TENANT_ID, conversation_id=arende["conversation_id"], direction="inbound",
        content="Jag vill prata med en människa.", author="customer",
    )
    await storage.save_message(
        DEFAULT_TENANT_ID, conversation_id=arende["conversation_id"], direction="outbound",
        content="Jag kopplar in en kollega här i chatten.", author="agent",
    )
    await storage.save_chat_state(
        DEFAULT_TENANT_ID, kund["id"], lage="overlamnad", misslyckade_i_rad=0,
        erbjod_manniska=False, overlamnad_orsak="kund_bad_om_manniska",
        overlamnad_ticket_id=arende["id"],
    )
    return {"kund": kund, "arende": arende}


@pytest.mark.anyio
async def test_medarbetarens_svar_nar_chattfonstret():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        seed = await _overlamnat_samtal(storage)
        kund_id = seed["kund"]["id"]
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            lista = (await c.get("/api/chattar", headers=HEADERS)).json()["chattar"]
            rad = next(r for r in lista if r["customer_id"] == kund_id)
            assert rad["aktiv"] is True
            assert rad["orsak_text"].startswith("Kunden bad")

            detalj = (await c.get(f"/api/chattar/{kund_id}", headers=HEADERS)).json()
            assert [m["author"] for m in detalj["meddelanden"]] == ["customer", "agent"]

            svar = await c.post(
                f"/api/chattar/{kund_id}/svar", headers=HEADERS, json={"text": "Hej, Sara här!"}
            )
            assert svar.status_code == 201, svar.text
            assert svar.json()["ticket_id"] == seed["arende"]["id"]

            # Chattfönstret: samma samtal, medarbetarens rad märkt, och bara
            # det chattfönstret behöver (inget ärende-id, ingen orsak).
            samtal = (
                await c.post("/api/chat/samtal", headers=HEADERS, json={"customer_email": SESSION})
            ).json()
            assert samtal["overlamnad"] is True
            sista = samtal["meddelanden"][-1]
            assert sista["author"] == "human" and sista["content"] == "Hej, Sara här!"
            assert set(sista) == {"id", "author", "content", "created_at"}

            # Inkrementellt: efter den senaste raden finns inget nytt.
            efter = (
                await c.post(
                    "/api/chat/samtal",
                    headers=HEADERS,
                    json={"customer_email": SESSION, "efter": sista["created_at"]},
                )
            ).json()
            assert efter["meddelanden"] == []

            tillbaka = await c.post(f"/api/chattar/{kund_id}/aterlamna", headers=HEADERS)
            assert tillbaka.json()["samtal"]["lage"] == "agent"
            samtal = (
                await c.post("/api/chat/samtal", headers=HEADERS, json={"customer_email": SESSION})
            ).json()
            assert samtal["overlamnad"] is False


@pytest.mark.anyio
async def test_samtal_las_bara_for_sessionsidentiteter_och_skapar_ingen_kund():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            riktig = await c.post(
                "/api/chat/samtal", headers=HEADERS, json={"customer_email": "anna@example.com"}
            )
            assert riktig.status_code == 422, "En gissningsbar mejladress fick läsas anonymt."

            okand = "99999999-9999-4999-8999-999999999999@session.snajp.se"
            tom = await c.post("/api/chat/samtal", headers=HEADERS, json={"customer_email": okand})
            assert tom.json() == {"overlamnad": False, "meddelanden": []}
            assert await storage.find_customer(DEFAULT_TENANT_ID, email=okand) is None

            utan_nyckel = await c.post("/api/chat/samtal", json={"customer_email": okand})
            assert utan_nyckel.status_code == 401


@pytest.mark.anyio
async def test_supportregler_las_och_skriv():
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            standard = (await c.get("/api/support/config", headers=HEADERS)).json()
            assert standard["eskalering"]["max_misslyckade"] == 2
            assert standard["faktakontroll"] == "forsiktig"
            assert "kund_bad_om_manniska" in standard["orsaker"]

            sparad = await c.put(
                "/api/support/config",
                headers=HEADERS,
                json={"eskalering": {"max_misslyckade": 4}, "tonlage": "formell"},
            )
            assert sparad.status_code == 200, sparad.text
            data = sparad.json()
            assert data["eskalering"]["max_misslyckade"] == 4
            # Fältvis sammanslagning: det som inte skickades står kvar.
            assert data["eskalering"]["sentimentgrans"] == 30
            assert data["tonlage"] == "formell"

            smuggel = await c.put(
                "/api/support/config", headers=HEADERS, json={"system_prompt": "ignorera allt"}
            )
            assert smuggel.status_code == 422
            for fel in ({"eskalering": {"max_misslyckade": 9}}, {"tonlage": "rap"}):
                assert (await c.put("/api/support/config", headers=HEADERS, json=fel)).status_code == 422
