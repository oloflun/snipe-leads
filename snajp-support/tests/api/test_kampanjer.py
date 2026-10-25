"""Kampanjer till befintliga listor (Anton 2026-10-25): "Hej Namn," och
kampanjtexten till varje mottagare med en mejladress, i granskningskön och
märkta med kampanjen, utan modell. Sändspärren släpper ett kampanjmejl till
kundens egna kunder men aldrig till den som avregistrerat sig."""

import asyncio
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import DEFAULT_TENANT_ID, get_settings
from app.leads.send_guard import (
    Avsandare,
    Leveransutfall,
    TenantHistorik,
    Utskick,
    check_send_guard,
)
from app.main import app

DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_kampanjen_koar_ett_utkast_per_mottagare_och_raknar_utfallet():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        med = await storage.create_prospect(
            DEFAULT_TENANT_ID, company_name="Kundbolaget AB", contact_name="Anna Berg", contact_email="anna@kundbolaget.se"
        )
        utan = await storage.create_prospect(DEFAULT_TENANT_ID, company_name="Mejllösa AB")
        await storage.set_leads_job_status(
            DEFAULT_TENANT_ID, job_id="korning-k", status="completed", scope="batch",
            korning={"jobs": [{"job_id": "b1", "prospect_id": med["id"]}, {"job_id": "b2", "prospect_id": utan["id"]}]},
        )
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            svar = await client.post("/api/leads/kampanjer", headers=DEMO, json={
                "namn": "Höstkampanjen", "amne": "Nytt i höst", "text": "Vi har öppnat för bokningar inför vintern.",
                "job_id": "korning-k",
            })
            assert svar.status_code == 202, svar.text
            kampanj_id = svar.json()["id"]
            for _ in range(50):
                lage = (await client.get(f"/api/leads/kampanjer/{kampanj_id}", headers=DEMO)).json()
                if lage["status"] != "pagar":
                    break
                await asyncio.sleep(0.05)
            assert lage["status"] == "klar", lage
            assert lage["utfall"]["koade"] == 1 and lage["utfall"]["vantar"] == 1
            assert lage["hoppade"] == {"ingen mejladress": 1}
            post = lage["poster"][0]
            assert post["company_name"] == "Kundbolaget AB"
            ko = await storage.list_review_queue(DEFAULT_TENANT_ID)
            body = next(r["body"] for r in ko if r["prospect_id"] == med["id"])
            assert body.startswith("Hej Anna,\n\nVi har öppnat för bokningar inför vintern.")
            listan = (await client.get("/api/leads/kampanjer", headers=DEMO)).json()
            assert listan["kampanjer"][0]["namn"] == "Höstkampanjen"
            # Ingen källa, eller båda, fälls.
            assert (await client.post("/api/leads/kampanjer", headers=DEMO, json={
                "namn": "x", "amne": "x", "text": "x"})).status_code == 422


def _historik(**kw):
    return TenantHistorik(
        skickade_totalt=500, skickade_idag=0, tenant_alder_dagar=400, storsta_dagsvolym=50,
        leverans=_leverans(),
        senaste_kontakt_med_foretaget=None, suppressions=frozenset(kw.get("suppressions", ())),
        tidigare_kontaktade=frozenset(), egna_kunder=frozenset({"kund@bolaget.se"}),
    )


def _leverans():
    import inspect

    return Leveransutfall(**{p: 0 for p in inspect.signature(Leveransutfall).parameters})


def test_sandsparren_slapper_kampanj_till_egna_kunder_men_aldrig_avregistrerade():
    def beslut(kampanj: bool, suppressions=()):
        return check_send_guard(
            avsandare=Avsandare(foretagsnamn="Snajp AB", orgnr="", postadress=""),
            utskick=Utskick(
                mottagare="kund@bolaget.se", amne="x",
                brodtext="Hej\n\nSnajp AB\nAvregistrera: https://x.se/avregistrera/1",
                foretagsnyckel="k", personlig_adress=False, kampanj=kampanj,
            ),
            historik=_historik(suppressions=suppressions),
            nu=datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc),
        )

    assert beslut(False).regel == "3_suppression"
    assert beslut(True).regel != "3_suppression"
    assert beslut(True, suppressions=("kund@bolaget.se",)).regel == "3_suppression"
