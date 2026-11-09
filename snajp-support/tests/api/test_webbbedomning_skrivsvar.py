"""Webbplatsbedömningen är hemlig även i SKRIVSVAREN (Fas 0-fyndet H9, 2026-11-09).

Antons beslut 2026-10-08: `webbrevision` och `webbniva` syns bara för
plattformsadmin, Umeå Webdesign och Alunix. Läsvägarna grindade fälten, men
svaren från ändra, befordra, degradera, skapa och "lista → prospekt" bar hela
prospektraden. Testet går genom HTTP-lagret mot MemoryStorage och håller
dessutom räkningen: varje `"prospect":` i api/leads.py ska gå genom grinden.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import DEFAULT_TENANT_ID, get_settings
from app.main import app

DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}
T = DEFAULT_TENANT_ID
HEMLIGT = ("webbrevision", "webbniva")

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _klient() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _bedomt_lead(storage, namn: str, **k) -> dict:
    lead = await storage.create_prospect(
        T, company_name=namn, contact_email=f"info@{namn.split()[0].lower()}.se", **k
    )
    # Prospektraden bär bedömningen i `webbrevision` (migration 094); `webbniva`
    # som egen kolumn finns på listrader och i webbpoolen, och göms av samma grind.
    return await storage.spara_bedomning(
        T, lead["id"], bedomning={"webbrevision": {"modernitet": 2, "webbniva": "akut", "brister": ["Liten text"]}}
    )


def _utan_hemligt(rad: dict) -> bool:
    return not any(falt in rad for falt in HEMLIGT)


async def test_andra_prospekt_svarar_utan_bedomningen(monkeypatch):
    monkeypatch.delenv("WEBBBEDOMNING_SYNLIG", raising=False)
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        lead = await _bedomt_lead(storage, "Tystbolaget AB")
        assert lead["webbrevision"]["webbniva"] == "akut", "förutsättningen: raden bär bedömningen i lagringen"

        async with _klient() as klient:
            svar = await klient.patch(
                f"/api/leads/prospects/{lead['id']}", headers=DEMO, json={"qualified": True}
            )
        assert svar.status_code == 200, svar.text
        assert _utan_hemligt(svar.json()["prospect"])
        # Lagringen är orörd: grinden gömmer, den raderar inte.
        assert (await storage.get_prospect(T, lead["id"]))["webbrevision"]["webbniva"] == "akut"


async def test_degradera_och_befordra_svarar_utan_bedomningen(monkeypatch):
    monkeypatch.delenv("WEBBBEDOMNING_SYNLIG", raising=False)
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        lead = await _bedomt_lead(storage, "Flyttbolaget AB")

        async with _klient() as klient:
            ned = await klient.post(f"/api/leads/prospects/{lead['id']}/degradera", headers=DEMO)
            igen = await klient.post(f"/api/leads/prospects/{lead['id']}/degradera", headers=DEMO)
            redan = await _bedomt_lead(storage, "Riktigtbolaget AB")
            upp = await klient.post(f"/api/leads/prospects/{redan['id']}/befordra", headers=DEMO)

        for svar in (ned, igen, upp):
            assert svar.status_code == 200, svar.text
            assert _utan_hemligt(svar.json()["prospect"])


async def test_synlig_kund_far_bedomningen_i_skrivsvaret(monkeypatch):
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        monkeypatch.setenv("WEBBBEDOMNING_SYNLIG", T)
        lead = await _bedomt_lead(storage, "Synligtbolaget AB")

        async with _klient() as klient:
            svar = await klient.patch(
                f"/api/leads/prospects/{lead['id']}", headers=DEMO, json={"qualified": True}
            )
        assert svar.status_code == 200, svar.text
        assert svar.json()["prospect"]["webbrevision"]["webbniva"] == "akut"


def test_varje_prospektsvar_gar_genom_grinden():
    """En ny väg som svarar med en prospektrad ska inte kunna glömma grinden."""
    kalla = (Path(__file__).resolve().parents[2] / "app" / "api" / "leads.py").read_text(encoding="utf-8")
    ogrindade = [
        rad.strip()
        for rad in kalla.splitlines()
        if re.search(r'"prospect":\s', rad)
        and "_utan_dold_bedomning(" not in rad
        and "med_rollflagga(" not in rad
    ]
    assert not ogrindade, (
        "Prospektsvar utan grind för webbplatsbedömningen i api/leads.py:\n  "
        + "\n  ".join(ogrindade)
        + "\nSvara med `await _utan_dold_bedomning(request, tenant, rad)`."
    )
