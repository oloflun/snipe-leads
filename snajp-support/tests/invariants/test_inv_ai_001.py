"""INV-AI-001: ett supportsvar som går ut utan mänsklig granskning bär en
kodskriven upplysning om att en AI-assistent skrev det.

AI-förordningen (EU 2024/1689) art. 50.1, tillämplig från 2026-08-02: den som
interagerar direkt med ett AI-system ska informeras om det. Systemprompten
förbjuder agenten att utge sig för att vara människa, men en upplysning som
hänger på modellens goda vilja är ingen upplysning. Därför lägger processorn
raden i kod, efter signaturen, och bara på autosvaren: ett utkast som en
människa granskat och godkänt är människans svar.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.email_pipeline import processor, sender
from app.main import app

settings = get_settings()
DEMO = {"X-API-Key": settings.snajp_demo_api_key}

PAKETFRAGAN = (
    "Beställde för en vecka sedan och spårningen har inte "
    "uppdaterats på fyra dagar. När kommer paketet?"
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def skickat(monkeypatch):
    """Det som faktiskt lämnar sändvägen, oavsett om miljön levererar."""
    fangat: list[str] = []
    original = sender.skicka_supportsvar

    async def fanga(email, *, content, **kwargs):
        fangat.append(content)
        return await original(email, content=content, **kwargs)

    monkeypatch.setattr(sender, "skicka_supportsvar", fanga)
    # Godkännandevägen importerar namnet vid modulladdning.
    from app.api import drafts

    monkeypatch.setattr(drafts, "skicka_supportsvar", fanga, raising=False)
    return fangat


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _ingest(client, body: str) -> dict:
    skapad = await client.post(
        "/api/inbox/ingest",
        headers=DEMO,
        json={
            "from": "johan@example.com",
            "from_name": "Johan Berg",
            "subject": "Var är mitt paket?",
            "body": body,
        },
    )
    assert skapad.status_code == 201
    return (await client.get(f"/api/inbox/{skapad.json()['email_id']}", headers=DEMO)).json()


@pytest.mark.anyio
async def test_autosvaret_bar_upplysningen_efter_signaturen(skickat):
    async with app.router.lifespan_context(app):
        async with _client() as client:
            await client.put("/api/rules", headers=DEMO, json={"category": "leverans", "mode": "auto"})
            mejl = await _ingest(client, PAKETFRAGAN)

    assert mejl["status"] == "auto_sent"
    rad = processor.AI_UPPLYSNING["sv"]
    # Det som skickades, det som sparades: båda bär raden, exakt en gång.
    assert skickat and all(text.count(rad) == 1 for text in skickat)
    assert mejl["draft"]["content"].count(rad) == 1
    # Raden står sist, efter en orörd signatur.
    innehall = mejl["draft"]["content"]
    assert innehall.endswith(rad)
    signatur_slut = innehall.index("Vänliga hälsningar,")
    assert signatur_slut < innehall.index(rad)
    assert "Vänliga hälsningar,\n" in innehall


@pytest.mark.anyio
async def test_manniskogranskat_svar_far_ingen_upplysning(skickat):
    async with app.router.lifespan_context(app):
        async with _client() as client:
            await client.put("/api/rules", headers=DEMO, json={"category": "leverans", "mode": "draft"})
            mejl = await _ingest(client, PAKETFRAGAN)
            assert mejl["status"] == "awaiting_approval"
            assert processor.AI_UPPLYSNING["sv"] not in mejl["draft"]["content"]

            godkant = await client.post(f"/api/drafts/{mejl['draft']['id']}/approve", headers=DEMO, json={})
            assert godkant.status_code == 200

    assert skickat, "godkännandet skickade inget"
    for text in skickat:
        assert all(rad not in text for rad in processor.AI_UPPLYSNING.values())


@pytest.mark.anyio
async def test_citerad_upplysning_i_ett_svar_eskalerar_inte(skickat):
    """Kunden svarar ofta med originalet citerat. Upplysningen själv får inte
    läsas som en begäran om en människa."""
    async with app.router.lifespan_context(app):
        async with _client() as client:
            await client.put("/api/rules", headers=DEMO, json={"category": "leverans", "mode": "auto"})
            # Ombruten och citerad, som en mejlklient gör det.
            rad = processor.AI_UPPLYSNING["sv"]
            mitt = rad.index("prata")
            citat = "> " + rad[:mitt] + "\n> " + rad[mitt:]
            mejl = await _ingest(client, PAKETFRAGAN + "\n\n" + citat)
    assert mejl["status"] == "auto_sent"


@pytest.mark.anyio
async def test_fallen_sandning_blir_ett_utkast_utan_upplysning(monkeypatch):
    """Faller autosändningen granskar en människa utkastet. Då är det hennes
    svar och ska inte bära upplysningen."""

    async def faller(email, *, content, **kwargs):
        raise sender.SandningsFel("nere")

    monkeypatch.setattr(sender, "skicka_supportsvar", faller)
    async with app.router.lifespan_context(app):
        async with _client() as client:
            await client.put("/api/rules", headers=DEMO, json={"category": "leverans", "mode": "auto"})
            mejl = await _ingest(client, PAKETFRAGAN)
    assert mejl["status"] == "awaiting_approval"
    assert processor.AI_UPPLYSNING["sv"] not in mejl["draft"]["content"]


@pytest.mark.anyio
async def test_den_som_ber_om_en_manniska_far_en(skickat):
    """Upplysningen lovar att den som svarar och ber om en människa får en.
    Löftet hålls i kod, inte av modellens bedömning."""
    async with app.router.lifespan_context(app):
        async with _client() as client:
            await client.put("/api/rules", headers=DEMO, json={"category": "leverans", "mode": "auto"})
            mejl = await _ingest(client, PAKETFRAGAN + " Jag vill prata med en medarbetare.")
    assert mejl["status"] == "escalated"
    assert not skickat


def test_upplysningen_dubbleras_aldrig_och_finns_pa_bada_spraken():
    svar = "Hej Johan!\n\nPaketet kommer i morgon.\n\nVänliga hälsningar,\nCykelbutiken AB"
    en_gang = processor.med_ai_upplysning(svar, "sv")
    assert processor.med_ai_upplysning(en_gang, "sv") == en_gang
    assert processor.med_ai_upplysning(en_gang, "en") == en_gang
    assert en_gang.startswith(svar)

    engelska = processor.med_ai_upplysning("Hi Johan!\n\nTomorrow.", "en")
    assert engelska.endswith(processor.AI_UPPLYSNING["en"])
    # Okänt eller saknat språk får svenska, samma standard som resten av mejlet.
    assert processor.med_ai_upplysning(svar, None).endswith(processor.AI_UPPLYSNING["sv"])
