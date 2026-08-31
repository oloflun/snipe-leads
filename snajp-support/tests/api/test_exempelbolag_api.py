"""Ladda in exempelbolag och starta en testkörning på dem — hela vägen.

Det här är den väg en ny kund faktiskt tar: arbetsytan är tom, knappen heter
*Starta körning*, och svaret "Inga prospekt att köra på" är korrekt men
obrukbart. Exempelbolagen finns för att göra vägen framkomlig, och testerna
här mäter just framkomligheten — inte generatorn, som har egna tester i
tests/leads/test_exempelbolag.py.

Tre saker vaktas:

 1. Bolagen skapas med `origin='example'`. Utan markeringen kan utskicks-
    spärren inte skilja dem från riktiga prospekt.
 2. Vägen in kräver INTE en riktig LLM-nyckel, till skillnad från körningen
    den leder till. En demonstrationsfunktion som bara fungerar när allt annat
    redan fungerar demonstrerar ingenting.
 3. Efter inladdningen startar testkörningen. Det är hela poängen med
    funktionen, och det som 422:an blockerade innan den fanns.
"""

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.main import app

DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}

#: 40 tecken ASCII. is_simulation() är sann under 20 tecken och vid varje
#: tecken över 127 — den här passerar båda kontrollerna utan att vara en
#: riktig nyckel, och inget test här når nätverket.
FEJKAD_LIVE_NYCKEL = "sk-" + "a" * 37


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture
def live_llm(monkeypatch):
    """Låtsas att en riktig nyckel är satt, utan att någon nås.

    Leads-ytorna är grindade av `_require_live_llm()`. Utan den här fixturen
    svarar körningen 503 och testet hade mätt grinden i stället för vägen.
    """
    # Alla tre, inte bara nyckeln: `active_llm_key()` läser DEEPSEEK_API_KEY
    # först när providern ÄR deepseek, och defaulten i koden är openai. Ett
    # test som bara satte nyckeln blev grönt på en maskin med en .env och rött
    # på en utan — alltså inte hermetiskt.
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("MODEL", "deepseek-v4-flash")
    monkeypatch.setenv("DEEPSEEK_API_KEY", FEJKAD_LIVE_NYCKEL)
    get_settings.cache_clear()
    assert not get_settings().is_simulation(), "fixturen ska ge live-läge"
    yield
    get_settings.cache_clear()


async def _ladda_exempelbolag(client, **body) -> dict:
    svar = await client.post("/api/leads/prospects/exempel", headers=DEMO, json=body)
    assert svar.status_code == 201, svar.text
    return svar.json()


@pytest.mark.anyio
async def test_exempelbolag_skapas_med_origin_example():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            body = await _ladda_exempelbolag(client, limit=3)

            assert body["count"] == 3
            assert len(body["created"]) == 3
            for prospect in body["created"]:
                assert prospect["origin"] == "example"
                assert prospect["motivering"].startswith("Exempelbolag:")
                assert prospect["status"] == "new"

            listade = (await client.get("/api/leads/prospects", headers=DEMO)).json()["prospects"]
            skapade_id = {p["id"] for p in body["created"]}
            assert skapade_id <= {p["id"] for p in listade}


@pytest.mark.anyio
async def test_exempelbolag_vagras_utanfor_demo():
    """Kund- och admin-tenanter ska inte kunna skapa färdigskrivna exempelbolag."""
    async with app.router.lifespan_context(app):
        async with _client() as client:
            skapad = await client.post(
                "/api/keys",
                headers={"X-API-Key": get_settings().snajp_master_api_key},
                json={"tenant_name": "Inte Demo AB"},
            )
            assert skapad.status_code == 201, skapad.text
            key = skapad.json()["api_key"]
            svar = await client.post(
                "/api/leads/prospects/exempel",
                headers={"X-API-Key": key},
                json={"limit": 1},
            )
            assert svar.status_code == 403, svar.text
            assert "demon" in svar.json()["detail"].lower()


@pytest.mark.anyio
async def test_vagen_in_kraver_ingen_riktig_nyckel_men_korningen_gor_det():
    # Kontrasten ÄR testet. Står miljön i simuleringsläge — vilket dev ofta gör
    # — måste knappen som fyller arbetsytan ändå fungera.
    async with app.router.lifespan_context(app):
        async with _client() as client:
            assert (
                await client.post("/api/leads/prospects/exempel", headers=DEMO, json={"limit": 1})
            ).status_code == 201

            korning = await client.post(
                "/api/leads/runs/batch", headers=DEMO, json={"limit": 1, "is_test": True}
            )
            assert korning.status_code == 503
            assert "DEEPSEEK_API_KEY" in korning.json()["detail"]


@pytest.mark.anyio
async def test_overskrivningarna_styr_vilka_bolag_som_skapas():
    # Samma överskrivningar som körningen. Ett formulär som beskriver en
    # målgrupp och skapar bolag ur en annan är värre än inga bolag alls.
    async with app.router.lifespan_context(app):
        async with _client() as client:
            body = await _ladda_exempelbolag(
                client,
                limit=2,
                overrides={
                    "industries": ["Åkeri"],
                    "geography": ["Umeå"],
                    "roles": ["Transportchef"],
                    "anstallda_min": 5,
                    "anstallda_max": 25,
                },
            )

            motiveringar = " ".join(p["motivering"] for p in body["created"])
            assert "åkeri i Umeå" in motiveringar
            assert "5–25 anställda" in motiveringar
            assert all(p["contact_name"] == "Transportchef" for p in body["created"])


@pytest.mark.anyio
async def test_antalet_har_ett_tak_och_ett_golv():
    # Taket är lågt med flit: exempelbolag är en väg in, inte en lista att
    # arbeta ur. Femtio bolag ska komma från en körning mot riktiga källor.
    async with app.router.lifespan_context(app):
        async with _client() as client:
            for limit in (0, 11):
                svar = await client.post(
                    "/api/leads/prospects/exempel", headers=DEMO, json={"limit": limit}
                )
                assert svar.status_code == 422, limit


@pytest.mark.anyio
async def test_testkorningen_startar_pa_de_inladdade_bolagen(live_llm, monkeypatch):
    """Hela poängen: tom arbetsyta → exempelbolag → körningen går att starta.

    Jobben körs inte på riktigt — `_run_batch_prospect` byts mot en spion.
    Det som mäts är att körningen kommer FÖRBI 422:an och skapar ett jobb per
    inladdat bolag, inte vad agenten sedan gör med dem.
    """
    from app.api import leads as leads_api

    startade: list[str] = []

    # `is_test` står med i signaturen för att routen numera skickar den vidare.
    # Att den kommer FRAM mäts inte här: jobben startas med
    # asyncio.create_task, så spionen har inte hunnit köra när testet läser.
    # Den mätningen görs deterministiskt i tests/leads/test_batch_markering.py.
    async def _spion(state, job_id, tenant, *, prospect_id, scope, overrides, is_test=False):
        startade.append(prospect_id)

    monkeypatch.setattr(leads_api, "_run_batch_prospect", _spion)

    async with app.router.lifespan_context(app):
        async with _client() as client:
            tom = await client.post(
                "/api/leads/runs/batch", headers=DEMO, json={"limit": 3, "is_test": True}
            )
            assert tom.status_code == 422
            assert "söker" in tom.json()["detail"].lower() or "egna bolag" in tom.json()["detail"].lower()

            body = await _ladda_exempelbolag(client, limit=3)
            exempel_id = {p["id"] for p in body["created"]}

            korning = await client.post(
                "/api/leads/runs/batch",
                headers=DEMO,
                json={"limit": 3, "scope": "research_and_draft", "is_test": True},
            )
            assert korning.status_code == 202, korning.text
            sok_id = korning.json()["jobs"][0]["job_id"]
            klart = None
            for _ in range(80):
                data = (await client.get(f"/api/jobs/{sok_id}", headers=DEMO)).json()
                if data["status"] in ("completed", "failed"):
                    klart = data
                    break
                await asyncio.sleep(0.05)
            assert klart is not None and klart["status"] == "completed", klart
            jobb = klart["result"]["jobs"]
            assert len(jobb) == 3
            assert {j["prospect_id"] for j in jobb} == exempel_id


@pytest.mark.anyio
async def test_svaret_bar_falten_vyn_listar():
    """Kontraktet mellan endpointen och listan i `LeadsRunForm`.

    Vyn visar org.nr, ort, webbplats, antal anställda och en kort beskrivning
    per bolag — samma form som ett riktigt prospekt får efter research. Ett
    fält som tyst försvinner här blir ett tomt streck i en kundvänd lista, och
    det syns inte i något annat test: `origin`-testet ovan passerar oförändrat.

    De fyra första SPARAS på raden, de två sista räknas fram ur ICP:t och
    lämnas bara i svaret — sparade hade de blivit osanna nästa gång kunden
    ändrar sin målgrupp.
    """
    async with app.router.lifespan_context(app):
        async with _client() as client:
            body = await _ladda_exempelbolag(
                client,
                limit=2,
                overrides={"industries": ["Bygg"], "geography": ["Umeå"], "roles": ["Inköpschef"]},
            )

            for prospect in body["created"]:
                for falt in ("orgnr", "ort", "website", "anstallda", "beskrivning", "bransch"):
                    assert prospect.get(falt), f"{falt} saknas i svaret"

                assert prospect["ort"] == "Umeå"
                assert prospect["contact_name"] == "Inköpschef"
                assert isinstance(prospect["anstallda"], int)

                # Identiteten måste vara omöjlig att förväxla med ett riktigt
                # bolag. Se app/leads/exempelbolag.py om varför.
                assert prospect["website"].endswith(".example")
                with pytest.raises(Exception):
                    from app.leads.orgnr import validera_format

                    validera_format(prospect["orgnr"])
