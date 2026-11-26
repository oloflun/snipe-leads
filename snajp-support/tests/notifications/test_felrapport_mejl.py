"""Mejlet om en ny felrapport bär numret och länken, aldrig kundens text,
namn eller arbetsyta (planens del 5)."""

import asyncio
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.api import plattformsarenden
from app.config import get_settings
from app.main import app
from app.notifications import prioriterat_mejl

MASTER = {"X-API-Key": get_settings().snajp_master_api_key}

KUNDTEXT = {
    "rapportor_namn": "Hemliga Hanna Hansson",
    "kund_tenant_slug": "kund-hemlig99",
    "gjorde": "Klistrade in kundregistret med anna@exempel.se",
    "hande": "Sidan visade 0701234567",
    "vantade": "Att Hemliga Bolaget AB skulle sparas",
}


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_mejlets_text_har_bara_nummer_och_lank():
    arende_id = str(uuid.uuid4())
    mejl = prioriterat_mejl.felrapportmejl(
        nummer="F-K7TQ", arende_id=arende_id, tenant_id="hjalp-tenant", bas_url="https://app.example.test/"
    )
    assert mejl.amne() == "[PRIORITERAT] Ny felrapport"
    assert "F-K7TQ" in mejl.brodtext()
    assert f"https://app.example.test/admin?felrapport={arende_id}" in mejl.brodtext()
    assert prioriterat_mejl.felrapportlank("", arende_id) == ""


@pytest.mark.anyio
async def test_en_riktig_rapport_lacker_inget_till_mejlet(monkeypatch):
    prioriterat_mejl.nollstall_dubblettminne()
    skickat: list[prioriterat_mejl.PrioriteratMejl] = []

    async def fanga(mejl, nyckel, avsandare):
        skickat.append(mejl)

    # Resend-vägen konfigurerad, sändningen fångad: hela kedjan från vägen
    # till mejlets text körs, bara nätanropet byts ut.
    monkeypatch.setattr(prioriterat_mejl, "_resend_konfiguration", lambda: ("nyckel", "larm@example.test"))
    monkeypatch.setattr(prioriterat_mejl, "_skicka_via_resend", fanga)

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            hjalp = await c.post(
                "/api/keys",
                headers=MASTER,
                json={"tenant_name": "Snajp Hjälp", "slug": get_settings().hjalp_tenant_slug, "kraver_avtal": False},
            )
            h = {"X-API-Key": hjalp.json()["api_key"]}
            arbetsyta = str(uuid.uuid4())
            rapportor = str(uuid.uuid4())
            svar = await c.post(
                "/api/plattformsarenden",
                headers=h,
                json={
                    **KUNDTEXT,
                    "rapportor_user_id": rapportor,
                    "kund_workspace_id": arbetsyta,
                    "vy": "leads",
                    "roll": "owner",
                    "besok_av_admin": False,
                    "sida": "/dashboard/leads",
                    "bild": None,
                },
            )
            assert svar.status_code == 201
            await asyncio.gather(*list(plattformsarenden._pagaende))

    assert len(skickat) == 1
    hela = skickat[0].amne() + "\n" + skickat[0].brodtext()
    assert svar.json()["nummer"] in hela
    for varde in (*KUNDTEXT.values(), arbetsyta, rapportor, "Hemliga", "anna@", "0701234567"):
        assert varde not in hela, f"mejlet bär {varde!r}"
