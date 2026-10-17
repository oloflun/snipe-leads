"""Beställ leads-lista → säljlistan (migration 105, Sebbe 2026-10-06).

Körningen går i listspåret men raderna med FULL kontaktinformation läggs i
arbetsytans säljlista; listan själv (kalla='saljlista') visas aldrig under
"Dina listor" och varken lyfts till Iris eller kombineras.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.leads import _kraev_ej_crm, saljlista_kvalificerade
from app.config import DEFAULT_TENANT_ID, get_settings
from app.main import app
from app.storage.memory import MemoryStorage
from fastapi import HTTPException

DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}
pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


KOMPLETT = {
    "company_name": "Nordform AB",
    "orgnr": "556677-8899",
    "contact_name": "Karin Öhman",
    "contact_phone": "070-123 45 67",
    "contact_email": "karin@nordform.example",
    "signal_detalj": "VD:s mejl på sajten",
}


def test_bara_rader_med_allt_kvalificerar():
    rader = [
        KOMPLETT,
        {**KOMPLETT, "company_name": "Utan mejl AB", "contact_email": None},
        {**KOMPLETT, "company_name": "Utan orgnr AB", "orgnr": ""},
        {**KOMPLETT, "company_name": "Utan person AB", "contact_name": "  "},
        {**KOMPLETT, "company_name": "Utan nummer AB", "contact_phone": None},
    ]
    ut = saljlista_kvalificerade(rader, titel="Bygg i Umeå")
    assert [r["foretagsnamn"] for r in ut] == ["Nordform AB"]
    assert ut[0]["kontaktmail"] == "karin@nordform.example"
    assert "Bygg i Umeå" in ut[0]["anteckningar"] and "VD:s mejl" in ut[0]["anteckningar"]


async def test_fyll_pa_dedupliklerar_pa_orgnr_och_namn():
    storage = MemoryStorage()
    rader = saljlista_kvalificerade([KOMPLETT], titel="t")
    assert await storage.saljlista_fyll_pa(DEFAULT_TENANT_ID, rader) == 1
    # Samma orgnr med andra skiljetecken, och samma namn med annan skiftning.
    igen = saljlista_kvalificerade(
        [{**KOMPLETT, "orgnr": "5566778899"}, {**KOMPLETT, "company_name": "NORDFORM AB", "orgnr": ""}],
        titel="t",
    )
    assert await storage.saljlista_fyll_pa(DEFAULT_TENANT_ID, igen) == 0
    assert len(storage._saljlista[DEFAULT_TENANT_ID]) == 1


async def test_bestallningen_far_kalla_saljlista_och_doljs_for_iris(monkeypatch):
    from app.api import leads as leads_api

    monkeypatch.setattr(leads_api, "_require_live_llm", lambda: None)

    async def _ingen_budget(*a, **kw):
        return None

    monkeypatch.setattr(leads_api, "_kraev_leads_budget", _ingen_budget)
    # Själva bygget är inte det som testas; det får stå i kö ogjort.
    monkeypatch.setattr(leads_api, "_run_list_job", _ingen_budget)
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            svar = await client.post(
                "/api/leads/listor",
                headers=DEMO,
                json={
                    "titel": "Säljlistan växer",
                    "antal": 3,
                    "is_test": True,
                    "mal": "saljlista",
                    "overrides": {"industries": ["bygg"]},
                },
            )
            assert svar.status_code == 202, svar.text
            lista = await storage.get_lead_list(DEFAULT_TENANT_ID, svar.json()["list_id"])
    assert lista["kalla"] == "saljlista"
    with pytest.raises(HTTPException) as fel:
        _kraev_ej_crm(lista)
    assert fel.value.status_code == 409
