"""Leadslistornas läsväg (Sebbe 2026-11-15: "det får inte lagga, oavsett").

Uppmätt i development samma dag: Iris-listan var 9,6 MB i sex anrop efter
varandra, Översiktens munkdiagram hämtade samma 9,6 MB för att räkna, och
körningslistan var 2,8 MB för 100 körningar. Det som prövas här är att de
smala vägarna säger EXAKT samma sak som de fulla de ersätter:

- listläget (`?lista=1`) ger samma leads, samma utkaststatus och samma
  synlighet som den fulla listan, men inte researchen,
- fördelningen räknar samma leads som listan visar,
- körningslistan bär antal i stället för listor, och detaljen är oförändrad,
- Skickat-räkningen ger samma tal som Skickat-listan.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import DEFAULT_TENANT_ID, get_settings
from app.leads import listvy
from app.main import app
from app.storage.postgres import _prospektkolumner

pytestmark = pytest.mark.anyio
DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _klient() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _seeda_leads(storage) -> dict[str, str]:
    """Ett lead av varje sort som listans synlighet skiljer på."""
    t = DEFAULT_TENANT_ID
    ids = {}

    def satt(pid: str, **falt) -> None:
        # Researchens fält skrivs av kedjan, inte av update_prospect: direkt
        # på minneslagringens rad, som researchsteget lämnar den.
        next(p for p in storage.prospects[t] if p["id"] == pid).update(falt)

    ids["vanlig"] = (
        await storage.create_prospect(
            t,
            company_name="Vanliga AB",
            contact_email="info@vanliga.se",
            profil={"contact_phone": "0701234567"},
        )
    )["id"]
    satt(
        ids["vanlig"],
        motivering="Bolaget växer snabbt. De anställer tre säljare i höst och saknar ett CRM.",
        score_total=81,
        niva="A",
        lagesbeskrivning="Lång research som aldrig ska till listan.",
        score_breakdown=[{"kriterium": "storlek", "poang": 20}],
        webbrevision={"modernitet": 3, "brister": ["Ingen mobilvy", "Trasig länk"]},
    )
    ids["bortvald"] = (await storage.create_prospect(t, company_name="Bortvalda AB"))["id"]
    satt(ids["bortvald"], niva="C", disqualifiers=["För litet. Bara en anställd."])
    ids["arkiverad"] = (await storage.create_prospect(t, company_name="Arkiverade AB", contact_email="a@ark.se"))["id"]
    await storage.arkivera_prospekt(t, [ids["arkiverad"]], arkivera=True)
    ids["ring"] = (await storage.create_prospect(t, company_name="Ringbolaget AB", origin="ring"))["id"]
    ids["kontaktad"] = (await storage.create_prospect(t, company_name="Kontaktade AB", contact_email="k@k.se"))["id"]
    await storage.update_prospect(t, ids["kontaktad"], status="contacted")
    return ids


async def test_listlaget_ger_samma_leads_utan_researchen():
    async with app.router.lifespan_context(app):
        ids = await _seeda_leads(app.state.storage)
        async with _klient() as client:
            full = (await client.get("/api/leads/prospects?limit=1000", headers=DEMO)).json()
            smal = (await client.get("/api/leads/prospects?lista=1&limit=5000", headers=DEMO)).json()
            bortvalda = (await client.get("/api/leads/prospects?lista=1&bortvalda=1", headers=DEMO)).json()
            arkiverade = (await client.get("/api/leads/prospects?lista=1&arkiverade=1", headers=DEMO)).json()

    assert [p["id"] for p in smal["prospects"]] == [p["id"] for p in full["prospects"]]
    assert ids["vanlig"] in {p["id"] for p in smal["prospects"]}
    for gomd in ("bortvald", "arkiverad", "ring"):
        assert ids[gomd] not in {p["id"] for p in smal["prospects"]}, gomd
    assert [p["id"] for p in bortvalda["prospects"]] == [ids["bortvald"]]
    assert [p["id"] for p in arkiverade["prospects"]] == [ids["arkiverad"]]

    fulla = {p["id"]: p for p in full["prospects"]}
    for rad in smal["prospects"]:
        for tung in ("lagesbeskrivning", "score_breakdown", "jev", "signaler", "orgnr", "tenant_id"):
            assert tung not in rad, tung
        # Utkaststatus, status och tidpunkt är desamma som i den fulla raden.
        for falt in ("status", "utkast_status", "queue_item_id", "senaste_handelse_at", "company_name"):
            assert rad.get(falt) == fulla[rad["id"]].get(falt), falt

    vanlig = next(p for p in smal["prospects"] if p["id"] == ids["vanlig"])
    assert vanlig["motivering"] == "Bolaget växer snabbt."
    assert vanlig["score_total"] == 81 and vanlig["niva"] == "A"
    assert vanlig["contact_phone"] == "0701234567" and vanlig["contact_email"] == "info@vanliga.se"
    # Webbbedömningen är hemlig utom för webbyråerna (CLAUDE.md 2026-10-08):
    # demotenanten är ingen av dem, så den finns inte heller i listläget.
    assert "webbrevision" not in vanlig
    assert "webbrevision" not in fulla[ids["vanlig"]]

    # Bortvalda-panelen visar det första skälet helt, före motiveringen.
    bort = bortvalda["prospects"][0]
    assert bort["disqualifiers"] == ["För litet. Bara en anställd."]


async def test_listlaget_bar_webbbetyget_bara_for_webbyraerna(monkeypatch):
    """En webbyrå ser betyget och den första bristen — inget mer av revisionen."""
    from app.leads import webbpool

    async def far_se(_storage, _tenant_id):
        return True

    monkeypatch.setattr(webbpool, "far_se", far_se)
    async with app.router.lifespan_context(app):
        ids = await _seeda_leads(app.state.storage)
        async with _klient() as client:
            smal = (await client.get("/api/leads/prospects?lista=1", headers=DEMO)).json()
    vanlig = next(p for p in smal["prospects"] if p["id"] == ids["vanlig"])
    assert vanlig["webbrevision"] == {"modernitet": 3, "brister": ["Ingen mobilvy"]}


async def test_listlaget_ger_tusentals_leads_i_ett_anrop():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        for i in range(1200):
            await storage.create_prospect(DEFAULT_TENANT_ID, company_name=f"Massbolag {i} AB")
        async with _klient() as client:
            svar = (await client.get("/api/leads/prospects?lista=1&limit=5000", headers=DEMO)).json()
            vanlig = (await client.get("/api/leads/prospects?limit=5000", headers=DEMO)).json()
    assert len(svar["prospects"]) >= 1200 and svar["fler"] is False
    # Det fulla läget behåller sitt tak, så att en stor sida aldrig bär researchen.
    assert len(vanlig["prospects"]) <= 1000 and vanlig["fler"] is True


async def test_fordelningen_raknar_samma_leads_som_listan():
    async with app.router.lifespan_context(app):
        await _seeda_leads(app.state.storage)
        async with _klient() as client:
            lista = (await client.get("/api/leads/prospects?lista=1&limit=5000", headers=DEMO)).json()["prospects"]
            fordelning = (await client.get("/api/leads/prospects/fordelning", headers=DEMO)).json()

    assert fordelning["antal"] == len(lista)
    per_status: dict[str, int] = {}
    for p in lista:
        per_status[p["status"]] = per_status.get(p["status"], 0) + 1
    assert fordelning["status"] == per_status
    per_vag = {"bada": 0, "telefon": 0, "mejl": 0, "saknas": 0}
    for p in lista:
        per_vag[listvy.kontaktvag(p)] += 1
    assert fordelning["kontaktvag"] == per_vag
    assert fordelning["status"].get("contacted") == 1


async def test_korningslistan_bar_antal_och_detaljen_hela_listorna():
    korning = {
        "mal": 3, "levererade": 1, "undersokta": 4, "pagaende": 0, "klar": True,
        "tratt": [{"namn": "A", "steg": "bedomning", "skal": "för litet"}] * 3,
        "jobs": [{"job_id": "j1", "prospect_id": "p1"}, {"job_id": "j2", "prospect_id": "p2"}],
        "kandidater": [{"company_name": "Hemlig"}],
    }
    async with app.router.lifespan_context(app):
        await app.state.storage.set_leads_job_status(
            DEFAULT_TENANT_ID, job_id="k-sam", status="completed", scope="batch", korning=korning
        )
        async with _klient() as client:
            lista = (await client.get("/api/leads/korningar", headers=DEMO)).json()["korningar"]
            detalj = (await client.get("/api/leads/korningar?detalj=1", headers=DEMO)).json()["korningar"]
            en = (await client.get("/api/leads/korningar/k-sam", headers=DEMO)).json()

    rad = next(r for r in lista if r["job_id"] == "k-sam")["korning"]
    assert "tratt" not in rad and "jobs" not in rad and "kandidater" not in rad
    assert rad["tratt_antal"] == 3 and rad["jobs_antal"] == 2
    assert rad["mal"] == 3 and rad["levererade"] == 1 and rad["klar"] is True

    full = next(r for r in detalj if r["job_id"] == "k-sam")["korning"]
    assert len(full["tratt"]) == 3 and len(full["jobs"]) == 2 and "kandidater" not in full
    assert len(en["korning"]["tratt"]) == 3 and len(en["korning"]["jobs"]) == 2


async def test_skickat_rakningen_ger_samma_tal_som_listan():
    t = DEFAULT_TENANT_ID
    nu = datetime.now(timezone.utc)
    async with app.router.lifespan_context(app):
        storage = app.state.storage

        async def skickat(namn: str, nar: datetime, *, svar: bool) -> None:
            p = await storage.create_prospect(t, company_name=namn, contact_email=f"info@{namn.split()[0].lower()}.se")
            trad = await storage.ensure_outreach_thread(t, prospect_id=p["id"])
            koat = await storage.queue_outreach_message(
                t, thread_id=trad["id"], subject="Hej", body="Hej!", humanizer_variant="x",
                scheduled_at=nar, status="awaiting_review",
            )
            await storage.mark_outreach_message_sent(t, koat["message"]["id"], nar)
            if svar:
                await storage.record_inbound_reply(t, thread_id=trad["id"], body="Ring mig.")

        await skickat("Nyss AB", nu - timedelta(days=2), svar=True)
        await skickat("Tyst AB", nu - timedelta(days=3), svar=False)
        await skickat("Gammal AB", nu - timedelta(days=40), svar=True)

        async with _klient() as client:
            antal = (await client.get("/api/leads/skickat/antal?dagar=28", headers=DEMO)).json()
            rader = (await client.get("/api/leads/skickat?limit=500", headers=DEMO)).json()["skickat"]

    grans = nu - timedelta(days=28)
    i_fonstret = [
        r for r in rader
        if r.get("sent_at") and datetime.fromisoformat(str(r["sent_at"]).replace("Z", "+00:00")) >= grans
    ]
    assert antal["dagar"] == 28
    assert antal["skickat"] == len(i_fonstret) == 2
    assert antal["svarat"] == sum(1 for r in i_fonstret if r["svarat"]) == 1


def test_projektionen_vagrar_okanda_kolumner():
    assert _prospektkolumner(None) == "*"
    assert _prospektkolumner(("company_name", "status")) == "id, company_name, status"
    assert _prospektkolumner(listvy.LISTKOLUMNER).startswith("id, ")
    with pytest.raises(ValueError):
        _prospektkolumner(("company_name", "1; drop table prospects"))


def test_forsta_meningen_som_vyn():
    assert listvy.forsta_mening("Ett. Två.") == "Ett."
    assert listvy.forsta_mening("Utan slut") == "Utan slut"
    assert listvy.forsta_mening("v2.5 är bäst! Sedan") == "v2.5 är bäst!"
    assert listvy.forsta_mening(None) is None
    assert len(listvy.forsta_mening("x" * 2000)) == listvy.MENINGSTAK
