"""Samtidiga körningar och workers (Sebbes krav 2026-10-06).

Flera användare på samma konto ska kunna köra agenter samtidigt, och
leads_workers > 1 betyder att två barn i SAMMA körning kan rapportera
parallellt. Motorns tillstånd uppdateras med läs-ändra-skriv
(_las_korning → mutera → _spara_korning), så utan ett lås per körning
skriver den sist sparande över den andras rapport: `pagaende` går aldrig
till noll och körningen står i 'processing' för evigt — exakt det
spårlösa slut INV-JOB-003 finns för att ta bort.

  a) två barn som rapporterar samtidigt räknas båda,
  b) två samtidiga påfyllningar (barnrapport + väckning) köar inte
     samma kandidat två gånger,
  c) olika körningar delar inte lås — de får gå parallellt.

Storagen i testerna släpper event-loopen mellan läsning och skrivning
(asyncio.sleep(0)), som Postgres/Redis gör i drift; utan det går
MemoryStorage-anropen klart utan avbrott och kapplöpningen syns aldrig.
"""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

from app.api import leads as leads_api
from app.jobs.store import MemoryJobStore
from app.leads import korning as korningsmodul
from app.storage.memory import MemoryStorage

pytestmark = pytest.mark.anyio
TENANT = {"tenant_id": "00000000-0000-0000-0000-00000000c4c4", "tenant_name": "Parallellbyrån"}
TID = TENANT["tenant_id"]


@pytest.fixture
def anyio_backend():
    return "asyncio"


class _VaxlandeStorage:
    """MemoryStorage som beter sig som Postgres i de två avseenden som
    gör kapplöpningen synlig: varje anrop släpper event-loopen, och varje
    läsning ger en FÄRSK avkodning (MemoryStorage lämnar annars ut en
    referens till samma dict, så två läsare delar mutationer de aldrig
    hade delat i drift)."""

    def __init__(self) -> None:
        self._inner = MemoryStorage()

    def __getattr__(self, namn):
        attr = getattr(self._inner, namn)
        if not callable(attr) or not asyncio.iscoroutinefunction(attr):
            return attr

        async def _vaxla(*a, **k):
            await asyncio.sleep(0)
            resultat = await attr(*a, **k)
            await asyncio.sleep(0)
            if isinstance(resultat, dict):
                resultat = json.loads(json.dumps(resultat, default=str))
            return resultat

        return _vaxla


def _bolag(namn: str) -> dict:
    from tests.orgnr_fixtur import orgnr_for

    slug = namn.lower().replace(" ", "")
    return {
        "company_name": namn, "website": f"https://{slug}.se", "orgnr": orgnr_for(namn),
        "ort": "Göteborg", "postnr": "421 32", "contact_email": f"info@{slug}.se",
        "contact_level": "role_address", "contact_name": "Test Testsson", "contact_role": "VD",
        "anstallda": None,
    }


class _Kö:
    def __init__(self) -> None:
        self.poster: list[dict] = []

    async def enqueue(self, payload: dict) -> str:
        self.poster.append(payload)
        return str(len(self.poster))


async def _ny_korning(storage, namn: list[str], *, mal: int | None = None, pagaende: int = 0) -> str:
    job_id = f"batch-{len(storage.leads_job_ledger)}"
    k = korningsmodul.ny_korning(
        mal=mal if mal is not None else len(namn), scope="research", overrides=None, is_test=True
    )
    k["kandidater"] = [_bolag(n) for n in namn]
    k["pagaende"] = pagaende
    await storage.set_leads_job_status(
        TID, job_id=job_id, status="processing", scope="batch", korning=k, is_test=True
    )
    return job_id


async def _k(storage, job_id: str) -> dict:
    return (await storage.get_leads_korning(TID, job_id))["korning"]


async def test_samtidiga_rapporter_tappas_inte():
    storage = _VaxlandeStorage()
    app_state = SimpleNamespace(jobs=MemoryJobStore(), storage=storage, leadsstrom=None)
    job_id = await _ny_korning(storage, [], mal=5, pagaende=2)

    async def rapport(barn: str, namn: str):
        await leads_api._rapportera_till_korning(
            app_state, TENANT, job_id, job_id=barn, namn=namn, leverbar=True, skal=None, fyll=False
        )

    await asyncio.gather(rapport("barn-1", "Ett AB"), rapport("barn-2", "Två AB"))
    k = await _k(storage, job_id)
    assert sorted(k["rapporterade"]) == ["barn-1", "barn-2"]
    assert k["pagaende"] == 0 and k["undersokta"] == 2 and k["levererade"] == 2


async def test_samtidiga_pafyllningar_koar_inte_dubbelt(monkeypatch):
    async def _hitta(*_a, **_k):
        return []

    monkeypatch.setattr(korningsmodul, "hitta_bolag", _hitta)
    storage = _VaxlandeStorage()
    ko = _Kö()
    app_state = SimpleNamespace(jobs=MemoryJobStore(), storage=storage, leadsstrom=ko)
    job_id = await _ny_korning(storage, ["Ett AB"], mal=1)

    await asyncio.gather(
        leads_api._fyll_pa(app_state, TENANT, job_id),
        leads_api._fyll_pa(app_state, TENANT, job_id),
    )
    k = await _k(storage, job_id)
    assert len(ko.poster) == 1, "samma kandidat köades två gånger av parallella påfyllningar"
    assert k["pagaende"] == 1 and len(k["jobs"]) == 1


async def test_olika_korningar_delar_inte_las():
    assert leads_api._korningslas("batch-a") is leads_api._korningslas("batch-a")
    assert leads_api._korningslas("batch-a") is not leads_api._korningslas("batch-b")
