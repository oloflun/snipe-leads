"""Eskaleringslarm från Snajp hamnar i Att hantera — aldrig som kundärende
med AI-utkast (migration 078, kundtest 2026-09-22)."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.email_pipeline.processor import ar_snajp_notis
from app.main import app

settings = get_settings()
DEMO = {"X-API-Key": settings.snajp_demo_api_key}

LARM_AMNE = "[PRIORITERAT] Supportärende eskalerat — Teknisk support"
LARM_KROPP = (
    "Tenant:  00000000-0000-4000-a000-000000000001\n"
    "Vad:     Ärende 123 (web) lämnades över till människa.\n"
    "Varför:  Kunden bad om att få prata med en människa.\n\n"
    "Det här mejlet kommer från Snajp. Ärendets innehåll står inte här "
    "— logga in och läs det i adminvyn."
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def test_igenkanningen_kraver_bade_amne_och_avsandarrad():
    assert ar_snajp_notis(LARM_AMNE, LARM_KROPP)
    # En kund som skriver [PRIORITERAT] i ämnet ska fortfarande få svar.
    assert not ar_snajp_notis("[PRIORITERAT] Min order är sen", "Hej, var är paketet?")
    # Avsändarraden utan prefix räcker inte heller.
    assert not ar_snajp_notis("Fråga", LARM_KROPP)


@pytest.mark.anyio
async def test_larm_far_egen_status_inget_utkast_och_syns_bara_i_fliken():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            larm = await client.post(
                "/api/inbox/ingest",
                headers=DEMO,
                json={"from": "kontakt@snajp.se", "from_name": "Snajp internlarm",
                      "subject": LARM_AMNE, "body": LARM_KROPP},
            )
            assert larm.status_code == 201
            kund = await client.post(
                "/api/inbox/ingest",
                headers=DEMO,
                json={"from": "kund@exempel.se", "subject": "Leveranstid?",
                      "body": "Hur lång är leveranstiden?"},
            )
            assert kund.status_code == 201

            detalj = (await client.get(f"/api/inbox/{larm.json()['email_id']}", headers=DEMO)).json()
            assert detalj["status"] == "att_hantera"
            assert detalj["draft"] is None, "ett larm får aldrig ett AI-utkast"
            assert "notis" in [d["event"] for d in detalj["decisions"]]
            assert "classified" not in [d["event"] for d in detalj["decisions"]]

            # Huvudlistan: kundmejlet men inte larmet.
            huvud = (await client.get("/api/inbox", headers=DEMO)).json()["emails"]
            amnen = {e["subject"] for e in huvud}
            assert "Leveranstid?" in amnen
            assert LARM_AMNE not in amnen

            # Fliken: bara larmet.
            flik = (await client.get("/api/inbox?status=att_hantera", headers=DEMO)).json()["emails"]
            assert [e["subject"] for e in flik] == [LARM_AMNE]
