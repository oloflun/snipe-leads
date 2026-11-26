"""Gemensamt för CRM-testerna: en app med minneslager, två kunder och nycklar.

Två kunder i varje test, eftersom det enda sättet att visa tenantisolering är
att den andra kunden finns och inte syns.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app import avtalsgrind
from app.api import crm, crm_v1, integrationer
from app.crm import nycklar, tillgang
from app.storage.memory import MemoryStorage

ALLA = ["crm:las", "crm:skriv", "crm:synk", "crm:admin"]

# Giltiga organisationsnummer (Luhn), påhittade bolag.
ORGNR_A, ORGNR_B, ORGNR_C = "556036-0793", "556016-0680", "556056-6258"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _nollstallt():
    crm_v1.nollstall_tak()
    avtalsgrind.nollstall_cache()
    tillgang.nollstall()
    yield
    crm_v1.nollstall_tak()
    avtalsgrind.nollstall_cache()
    tillgang.nollstall()


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(crm_v1.router)
    app.include_router(crm.router)
    # En vanlig kunddata-router, för att visa att en CRM-nyckel inte når den.
    app.include_router(integrationer.router)
    app.state.storage = MemoryStorage()
    return app


@pytest.fixture
def storage(app):
    return app.state.storage


class Kund:
    def __init__(self, app, tenant: dict, nyckel: str) -> None:
        self.app, self.tenant, self.nyckel = app, tenant, nyckel
        self.id = tenant["id"]

    def klient(self, nyckel: str | None = None) -> AsyncClient:
        """Kundens egen nyckel om inget annat sägs; tom sträng = ingen nyckel alls."""
        huvuden = {} if nyckel == "" else {"X-API-Key": nyckel or self.nyckel}
        return AsyncClient(transport=ASGITransport(app=self.app), base_url="http://test", headers=huvuden)

    async def ny_nyckel(self, omfang: list[str], namn: str = "prov") -> str:
        svar = await nycklar.skapa(self.app.state.storage, self.id, tenant_namn=self.tenant["name"],
                                   namn=namn, omfang=omfang)
        return svar["api_key"]


async def _kund(app, slug: str, namn: str, *, kraver_avtal: bool = False) -> Kund:
    tenant = await app.state.storage.create_tenant(slug=slug, name=namn, kraver_avtal=kraver_avtal)
    svar = await nycklar.skapa(app.state.storage, tenant["id"], tenant_namn=namn, namn="integration", omfang=ALLA)
    return Kund(app, tenant, svar["api_key"])


@pytest.fixture
async def buddy(app) -> Kund:
    return await _kund(app, "buddy", "Buddy")


@pytest.fixture
async def annan(app) -> Kund:
    return await _kund(app, "annan-kund", "Annan Kund AB")


@pytest.fixture
async def utan_avtal(app) -> Kund:
    return await _kund(app, "utan-avtal", "Utan Avtal AB", kraver_avtal=True)
