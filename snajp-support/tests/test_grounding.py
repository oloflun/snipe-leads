"""Grundningsspärrar: agenten får inte svara på ofärdigt underlag.

Bakgrund: ett skarpt testmail visade att modellen skrev "Garantitiden är tre år"
trots att kunskapsbasen bara sa "under garantitiden" — siffran var påhittad.
Prompten är skärpt, men en modell som ombeds låta bli kan ändå glida. Därför
finns en kodspärr som inte kan glida.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import PILOT_TENANT_ID, get_settings
from app.kb_templates import PLACEHOLDER_PREFIX
from app.main import app
from app.storage.memory import MemoryStorage

settings = get_settings()
PILOT_KEY = "snajp_pilot_grounding_test_key_123"
PILOT = {"X-API-Key": PILOT_KEY}


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def pilot(monkeypatch):
    monkeypatch.setattr(get_settings(), "snajp_pilot_api_key", PILOT_KEY, raising=False)


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.anyio
async def test_placeholder_kb_forces_escalation(pilot):
    """Svar som bygger på [PLATSHÅLLARE]-text får aldrig gå ut som färdigt."""
    async with app.router.lifespan_context(app):
        async with _client() as client:
            # Pilotens arbetsyta fylls med mallen — allt är platshållare.
            await client.post("/api/kb/template", headers=PILOT)

            r = await client.post(
                "/api/inbox/ingest",
                headers=PILOT,
                json={
                    "from": "kund@example.com",
                    "subject": "Fråga om garantitiden",
                    "body": "Hur lång är garantitiden på era hjärtstartare?",
                },
            )
            assert r.status_code == 201
            email_id = r.json()["email_id"]

            detail = (await client.get(f"/api/inbox/{email_id}", headers=PILOT)).json()
            assert detail["status"] == "escalated"
            reason = detail["classification"]["escalation_reason"] or ""
            assert "platshållare" in reason.lower()


@pytest.mark.anyio
async def test_real_content_is_answerable(pilot):
    """Motsatsen: färdigt material ska ge ett utkast, inte eskalering."""
    async with app.router.lifespan_context(app):
        async with _client() as client:
            await client.post(
                "/api/kb",
                headers=PILOT,
                json={
                    "articles": [
                        {
                            "title": "Garantitid",
                            "content": (
                                "Garantin på våra hjärtstartare gäller i åtta år från "
                                "leveransdatum och omfattar fabrikationsfel på enheten. "
                                "Elektroder och batteri är förbrukningsvaror."
                            ),
                            "category": "garanti",
                        }
                    ]
                },
            )
            r = await client.post(
                "/api/inbox/ingest",
                headers=PILOT,
                json={
                    "from": "kund2@example.com",
                    "subject": "Garantitid",
                    "body": "Hur lång är garantitiden på hjärtstartaren?",
                },
            )
            email_id = r.json()["email_id"]
            detail = (await client.get(f"/api/inbox/{email_id}", headers=PILOT)).json()
            assert detail["status"] == "awaiting_approval"
            assert detail["draft"]["status"] == "pending"


@pytest.mark.anyio
async def test_placeholder_prefix_is_detectable():
    """Kodspärren bygger på prefixet — det måste finnas i mallens artiklar."""
    storage = MemoryStorage()
    await storage.ensure_tenant(PILOT_TENANT_ID, slug="pilot", name="Pilot")
    from app.kb_templates import as_articles

    for article in as_articles(prefixed=True):
        assert article["content"].startswith(PLACEHOLDER_PREFIX)
