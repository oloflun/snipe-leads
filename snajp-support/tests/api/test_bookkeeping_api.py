"""Bokförings-API:t: åtkomstgrinden, periodrapporten och exporten.

Exempeldata följer regeln för leads exempelbolag: organisationsnumret har
medvetet fel kontrollsiffra (556677-8890; korrekt vore 9).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import DEFAULT_TENANT_ID, get_settings
from app.main import app

DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}
MASTER = {"X-API-Key": get_settings().snajp_master_api_key}


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _seed_kvitto(storage, tenant_id: str, *, brutto="1250.00", datum=date(2026, 3, 5)):
    """Ett godkänt kvitto med sitt verifikat. Byggt via lagringen och inte via
    API:t, eftersom uppladdningsvägen kräver ett LLM-anrop."""
    underlag = await storage.create_bk_underlag(
        tenant_id,
        sha256="0" * 64,
        filnamn="kvitto.pdf",
        mimetyp="application/pdf",
        status="klar",
        datum=datum,
        motpart="Eknäs Bygg Gruppen AB",
        brutto=Decimal(brutto),
        momssats=Decimal("0.25"),
        riktning="kostnad",
        kategori="varuinkop",
    )
    from app.bookkeeping.kontoplan import bygg_inkopsverifikat

    rader = bygg_inkopsverifikat(brutto=brutto, momssats="0.25", kategori="varuinkop")
    await storage.create_bk_verifikat(
        tenant_id,
        underlag_id=underlag["id"],
        serie="A",
        nummer="1",
        datum=datum,
        text="Inköp material",
        rader=[{"konto": r.konto, "debet": r.debet, "kredit": r.kredit, "text": r.text} for r in rader],
    )
    return underlag


# -- Åtkomst ---------------------------------------------------------------


@pytest.mark.anyio
@pytest.mark.parametrize(
    "vag",
    [
        "/api/bookkeeping/underlag",
        "/api/bookkeeping/period?fran=2026-03-01&till=2026-03-31",
        "/api/bookkeeping/period.sie?fran=2026-03-01&till=2026-03-31&foretagsnamn=X&orgnr=1",
    ],
)
async def test_utan_nyckel_svarar_401(vag):
    """Hela ytan är stängd utan nyckel. Ett kvitto bär personnummer och
    lönebelopp — samma sekretessnivå som supportens kunddata, inte lägre."""
    async with app.router.lifespan_context(app):
        async with _client() as client:
            assert (await client.get(vag)).status_code == 401


@pytest.mark.anyio
async def test_masternyckeln_nar_inte_kunddata():
    """Master är administrativ och har ingen tenant. Utan den här grinden hade
    en administrativ nyckel kunnat läsa vilket bolags kvitton som helst."""
    async with app.router.lifespan_context(app):
        async with _client() as client:
            svar = await client.get("/api/bookkeeping/underlag", headers=MASTER)
            assert svar.status_code == 403


@pytest.mark.anyio
async def test_ogiltig_nyckel_svarar_401():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            svar = await client.get(
                "/api/bookkeeping/underlag", headers={"X-API-Key": "snajp_live_pahittad"}
            )
            assert svar.status_code == 401


@pytest.mark.anyio
async def test_ett_annat_bolags_kvitton_syns_inte():
    """Tenant-isolering, mätt och inte antagen."""
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        await _seed_kvitto(storage, "en-annan-tenant")
        async with _client() as client:
            svar = await client.get("/api/bookkeeping/underlag", headers=DEMO)
            assert svar.status_code == 200
            assert svar.json()["underlag"] == []


# -- Periodrapport ---------------------------------------------------------


@pytest.mark.anyio
async def test_periodrapport_med_handraknat_facit():
    """1 250 kr inkl. 25 % moms: netto 1 000, moms 250."""
    async with app.router.lifespan_context(app):
        await _seed_kvitto(app.state.storage, DEFAULT_TENANT_ID)
        async with _client() as client:
            svar = await client.get(
                "/api/bookkeeping/period?fran=2026-03-01&till=2026-03-31", headers=DEMO
            )
            assert svar.status_code == 200
            rapport = svar.json()
            assert rapport["status"] == "klar"
            assert rapport["summor"]["kostnader"] == "1000.00"
            assert rapport["summor"]["ingaende_moms"] == "250.00"
            assert rapport["summor"]["resultat_fore_skatt"] == "-1000.00"


# -- Rensningen -----------------------------------------------------------


@pytest.mark.anyio
async def test_rensning_nollar_perioden_och_tar_verifikaten_med_sig():
    """Vyns Rensa-knapp. Summorna ÄR underlagen, så bägge ska vara borta.

    Verifikatet kontrolleras särskilt: i Postgres följer det med via
    `on delete cascade`, i minnet skrivs kaskaden för hand. Blir den kvar
    fortsätter perioden räknas ur poster vars underlag inte längre finns —
    och den divergensen syns bara om testet frågar efter verifikaten.
    """
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        await _seed_kvitto(storage, DEFAULT_TENANT_ID)
        async with _client() as client:
            svar = await client.delete(
                "/api/bookkeeping/period?fran=2026-03-01&till=2026-03-31", headers=DEMO
            )
            assert svar.status_code == 200
            assert svar.json() == {"raderade": 1}

            rapport = await client.get(
                "/api/bookkeeping/period?fran=2026-03-01&till=2026-03-31", headers=DEMO
            )
            assert rapport.json()["summor"]["kostnader"] == "0.00"
            assert rapport.json()["antal_underlag"] == 0
            assert rapport.json()["antal_verifikat"] == 0

            lista = await client.get("/api/bookkeeping/underlag", headers=DEMO)
            assert lista.json()["underlag"] == []

        assert await storage.list_bk_verifikat(DEFAULT_TENANT_ID) == []


@pytest.mark.anyio
async def test_rensningen_lamnar_en_annan_period_ifred():
    """Urvalet är intervallets, inte tenantens allt."""
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        await _seed_kvitto(storage, DEFAULT_TENANT_ID, datum=date(2026, 3, 5))
        await _seed_kvitto(
            storage, DEFAULT_TENANT_ID, brutto="500.00", datum=date(2026, 4, 5)
        )
        async with _client() as client:
            svar = await client.delete(
                "/api/bookkeeping/period?fran=2026-03-01&till=2026-03-31", headers=DEMO
            )
            assert svar.json() == {"raderade": 1}

            kvar = await client.get(
                "/api/bookkeeping/underlag?fran=2026-04-01&till=2026-04-30", headers=DEMO
            )
            assert [r["datum"] for r in kvar.json()["underlag"]] == ["2026-04-05"]


@pytest.mark.anyio
async def test_rensningen_nar_inte_ett_annat_bolag():
    """Tenant-isolering på raderingsvägen, mätt och inte antagen. Ett fel här
    är värre än ett fel på läsvägen: det syns inte, det försvinner."""
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        await _seed_kvitto(storage, "en-annan-tenant")
        async with _client() as client:
            svar = await client.delete(
                "/api/bookkeeping/period?fran=2026-03-01&till=2026-03-31", headers=DEMO
            )
            assert svar.status_code == 200
            assert svar.json() == {"raderade": 0}

        assert len(await storage.list_bk_underlag("en-annan-tenant")) == 1


@pytest.mark.anyio
async def test_rensningen_tar_med_underlag_utan_datum():
    """Ett fällt underlag saknar datum och visas ändå i listan. Rensar knappen
    ett snävare urval än vyn visade blir just granskningskön kvar."""
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        await storage.create_bk_underlag(
            DEFAULT_TENANT_ID,
            sha256="1" * 64,
            filnamn="suddigt.jpg",
            mimetyp="image/jpeg",
            status="granska_manuellt",
            anmarkning="Datum gick inte att läsa.",
        )
        async with _client() as client:
            svar = await client.delete(
                "/api/bookkeeping/period?fran=2026-03-01&till=2026-03-31", headers=DEMO
            )
            assert svar.json() == {"raderade": 1}

            lista = await client.get("/api/bookkeeping/underlag", headers=DEMO)
            assert lista.json()["underlag"] == []


@pytest.mark.anyio
async def test_rensning_utan_nyckel_svarar_401():
    """Raderingsvägen står bakom samma grind som läsvägarna."""
    async with app.router.lifespan_context(app):
        async with _client() as client:
            svar = await client.delete(
                "/api/bookkeeping/period?fran=2026-03-01&till=2026-03-31"
            )
            assert svar.status_code == 401


@pytest.mark.anyio
async def test_belopp_ar_strangar_i_json_aldrig_tal():
    """Ett JSON-tal blir en float hos mottagaren, och webbläsaren räknar
    0.1 + 0.2 lika fel som Python. Premissen slutar inte gälla för att värdet
    passerat ett nätverk."""
    async with app.router.lifespan_context(app):
        await _seed_kvitto(app.state.storage, DEFAULT_TENANT_ID)
        async with _client() as client:
            rapport = (
                await client.get(
                    "/api/bookkeeping/period?fran=2026-03-01&till=2026-03-31", headers=DEMO
                )
            ).json()
            for nyckel, varde in rapport["summor"].items():
                if nyckel == "antal_poster":
                    continue
                assert isinstance(varde, str), f"{nyckel} kom som {type(varde).__name__}"


@pytest.mark.anyio
async def test_trasigt_underlag_gor_perioden_granskningsbar_inte_klar():
    """Det testfall briefen kräver, hela vägen genom API:t.

    Ett underlag utan momssats får inte ge en snygg summa — då hade en
    människa skrivit under en rapport som saknar en post.
    """
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        await _seed_kvitto(storage, DEFAULT_TENANT_ID)
        await storage.create_bk_underlag(
            DEFAULT_TENANT_ID,
            sha256="1" * 64,
            filnamn="otydligt.pdf",
            mimetyp="application/pdf",
            status="granska_manuellt",
            datum=date(2026, 3, 12),
            motpart="Okänd",
            brutto=Decimal("499.00"),
            momssats=None,  # står inte på kvittot
            riktning="kostnad",
            kategori="varuinkop",
        )
        async with _client() as client:
            rapport = (
                await client.get(
                    "/api/bookkeeping/period?fran=2026-03-01&till=2026-03-31", headers=DEMO
                )
            ).json()
            assert rapport["status"] == "granska_manuellt"
            assert any("momssats" in b for b in rapport["brister"])
            # Det fällda underlaget bidrar INTE med ett gissat belopp.
            assert rapport["summor"]["kostnader"] == "1000.00"


@pytest.mark.anyio
async def test_forbehallet_foljer_med_varje_svar():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            svar = (await client.get("/api/bookkeeping/underlag", headers=DEMO)).json()
            assert "ersätter inte en" in svar["forbehall"]


# -- SIE4-export -----------------------------------------------------------


@pytest.mark.anyio
async def test_sie_exporten_ar_cp437_och_balanserar():
    async with app.router.lifespan_context(app):
        await _seed_kvitto(app.state.storage, DEFAULT_TENANT_ID)
        async with _client() as client:
            svar = await client.get(
                "/api/bookkeeping/period.sie?fran=2026-03-01&till=2026-03-31"
                "&foretagsnamn=Eknäs Bygg Gruppen AB&orgnr=556677-8890",
                headers=DEMO,
            )
            assert svar.status_code == 200
            text = svar.content.decode("cp437")
            assert "#FORMAT PC8" in text
            assert "#TRANS 4010 {} 1000.00" in text
            summa = sum(
                Decimal(rad.split()[-1])
                for rad in text.splitlines()
                if rad.strip().startswith("#TRANS")
            )
            assert summa == Decimal(0)


@pytest.mark.anyio
async def test_fald_period_exporteras_inte():
    """Mottagarsystemet hade avvisat filen ändå — men då på kundens skärm, i
    deras program, och det är för sent."""
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        await _seed_kvitto(storage, DEFAULT_TENANT_ID)
        await storage.create_bk_underlag(
            DEFAULT_TENANT_ID,
            sha256="2" * 64,
            filnamn="halv.pdf",
            mimetyp="application/pdf",
            status="granska_manuellt",
            datum=date(2026, 3, 20),
            motpart="Okänd",
            brutto=Decimal("100.00"),
            riktning="kostnad",
            kategori="varuinkop",
        )
        async with _client() as client:
            svar = await client.get(
                "/api/bookkeeping/period.sie?fran=2026-03-01&till=2026-03-31"
                "&foretagsnamn=Test&orgnr=556677-8890",
                headers=DEMO,
            )
            assert svar.status_code == 409
            assert svar.json()["detail"]["status"] == "granska_manuellt"


# -- Uppladdningsgrinden ---------------------------------------------------


@pytest.mark.anyio
async def test_okant_filformat_avvisas_med_namnet_pa_det_som_gar():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            svar = await client.post(
                "/api/bookkeeping/underlag",
                headers=DEMO,
                files={"fil": ("bok.xlsx", b"PK\x03\x04", "application/vnd.ms-excel")},
            )
            assert svar.status_code == 422
            assert "application/pdf" in svar.json()["detail"]


# -- Dubblettspärren -------------------------------------------------------
#
# Sätts FÖRE textutvinningen i `ta_emot_underlag`, så testet behöver ingen
# LLM-mock: en fil vars sha256 redan finns avvisas innan modellen kommer in.


@pytest.mark.anyio
async def test_samma_fil_tva_ganger_avvisas_med_422():
    """Ett dubblerat underlag blir en dubblerad kostnad i periodrapporten —
    trovärdiga men felaktiga tal, samma felfamilj som INV-BOOK-002 stoppar."""
    from app.bookkeeping.underlag import sha256_av

    data = b"%PDF-1.4 samma kvitto tva ganger"
    async with app.router.lifespan_context(app):
        await app.state.storage.create_bk_underlag(
            DEFAULT_TENANT_ID,
            sha256=sha256_av(data),
            filnamn="kvitto.pdf",
            mimetyp="application/pdf",
            status="klar",
            datum=date(2026, 3, 5),
        )
        async with _client() as client:
            svar = await client.post(
                "/api/bookkeeping/underlag",
                headers=DEMO,
                files={"fil": ("kvitto-igen.pdf", data, "application/pdf")},
            )
            assert svar.status_code == 422
            assert "redan uppladdad" in svar.json()["detail"]
            assert "kvitto.pdf" in svar.json()["detail"]

        # Ingen ny rad skrevs — spärren avvisar, den flaggar inte.
        assert len(await app.state.storage.list_bk_underlag(DEFAULT_TENANT_ID)) == 1


@pytest.mark.anyio
async def test_dubblettsparren_ser_inte_ett_annat_bolags_fil():
    """Spärren är per tenant. Slog den över tenantgränsen hade den dels
    blockerat legitima uppladdningar, dels LÄCKT: ett 422 med den andra
    tenantens filnamn hade bekräftat vad ett annat bolag laddat upp.

    Prövas på lagringsnivå — det är `get_bk_underlag_by_sha256` som bär
    gränsen, och API-vägen ovanför den kräver en LLM-mock som inte skulle
    bevisa mer om just isoleringen."""
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        await storage.create_bk_underlag(
            "en-annan-tenant",
            sha256="f" * 64,
            filnamn="hemlig.pdf",
            mimetyp="application/pdf",
            status="klar",
        )
        assert await storage.get_bk_underlag_by_sha256(DEFAULT_TENANT_ID, "f" * 64) is None
        traff = await storage.get_bk_underlag_by_sha256("en-annan-tenant", "f" * 64)
        assert traff is not None and traff["filnamn"] == "hemlig.pdf"
