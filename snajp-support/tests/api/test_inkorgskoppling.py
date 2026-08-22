"""Inkorgssynken: kundens egna inkorgar, och ett ärligt svar när ingen finns.

Bakgrunden är en felrapport från den skarpa dev-deployen: knappen "Synka
inkorg" i kundtjänstvyn svarade

    IMAP är inte konfigurerat (IMAP_HOST/USER/PASSWORD)

för varje kund. Två saker var fel, och de testas var för sig nedan:

1. Routen synkade mot GLOBALA miljövariabler i stället för mot den frågande
   kundens inkorgar. I en flerkundsinstallation är det fel brevlåda — hade de
   globala värdena varit satta hade alla kunders synk hämtat SAMMA mail.
2. Felmeddelandet namngav miljövariabler som kunden varken kan se eller sätta.

`/api/inbox/mailboxes` finns för att UI:t ska kunna fråga FÖRE klicket i
stället för att visa en knapp som alltid misslyckas.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.main import app

settings = get_settings()
DEMO = {"X-API-Key": settings.snajp_demo_api_key}


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.anyio
async def test_synk_utan_kopplad_inkorg_namnger_inga_miljovariabler():
    """Svaret ska gå att läsa för en kund, inte för den som driftar tjänsten."""
    async with app.router.lifespan_context(app):
        async with _client() as client:
            svar = await client.post("/api/inbox/sync", headers=DEMO)

    assert svar.status_code == 200
    kropp = svar.json()
    assert kropp["connected"] is False
    assert kropp["fetched"] == 0

    fel = kropp["error"]
    for lackande in ("IMAP_HOST", "IMAP_USER", "IMAP_PASSWORD", "env"):
        assert lackande not in fel, f"felmeddelandet läcker driftdetaljen {lackande}: {fel}"
    assert "inkorg" in fel.lower()


@pytest.mark.anyio
async def test_mailboxes_sager_att_ingenting_ar_kopplat():
    """UI:t ska kunna skilja "ingen inkorg" från "inkorg som inte svarar"."""
    async with app.router.lifespan_context(app):
        async with _client() as client:
            svar = await client.get("/api/inbox/mailboxes", headers=DEMO)

    assert svar.status_code == 200
    kropp = svar.json()
    assert kropp["kan_synka"] is False
    assert kropp["mailboxes"] == []


@pytest.mark.anyio
async def test_mailboxes_kraver_nyckel():
    """Adresserna är kunddata. Utan nyckel ska routen inte svara alls."""
    async with app.router.lifespan_context(app):
        async with _client() as client:
            svar = await client.get("/api/inbox/mailboxes")

    assert svar.status_code == 401


@pytest.mark.anyio
async def test_mailboxes_lacker_aldrig_ett_losenord():
    """Ett fältnamn som liknar ett lösenord ska inte finnas i svaret alls.

    Lösenordet bor i env under IMAP_PASSWORD_<SLUG> just för att en
    läsbehörighet på ss_mailboxes inte ska räcka för att läsa kundens mail. Ett
    API som skickar med det gör den spärren meningslös.
    """
    async with app.router.lifespan_context(app):
        async with _client() as client:
            await client.post("/api/inbox/mock", headers={**DEMO, "X-Snajp-Demo": "true"})
            svar = await client.get("/api/inbox/mailboxes", headers=DEMO)

    text = svar.text.lower()
    for hemligt in ("password", "losenord", "lösenord", "secret"):
        assert hemligt not in text, f"svaret innehåller {hemligt}"
