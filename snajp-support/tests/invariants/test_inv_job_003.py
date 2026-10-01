"""INV-JOB-003 — En körnings tillstånd finns i liggaren efter varje steg;
Redis-TTL:n är aldrig enda platsen.

## Buggen den här stänger

Anton startade en Iris-körning 2026-09-30 som inte hann bli klar. När han
kom tillbaka fanns inget spår: inga nya leads, ingen felorsak, ingen lista
över körningar. Motorns tillstånd (`korning`) bodde bara i jobbstoret
(Redis, TTL 3 600 s) och i LeadsRunForm.tsx:s React-state, och liggarens
batchrad sattes till 'completed' i samma ögonblick som motorn STARTADE.

Skyddet, testat här mot den riktiga motorn (`_run_batch` → `_fyll_pa` →
prospektjobb → `_rapportera_till_korning`) med fejkad sökning och research:
  a) batchraden står i 'processing' med tillstånd medan motorn arbetar,
  b) tillståndet överlever att jobbstoret töms (= Redis-TTL),
  c) ett fel i körningen ger status 'failed' och en felorsak i klartext,
  d) körningslistan bär batch- och listrader, aldrig prospektjobben.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from app.api import leads as leads_api
from app.jobs.store import MemoryJobStore
from app.leads import korning as korningsmodul
from app.storage.memory import MemoryStorage

pytestmark = pytest.mark.anyio
TENANT = {"tenant_id": "00000000-0000-0000-0000-00000000b2b2", "tenant_name": "Testbyrån"}


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _bolag(namn: str) -> dict:
    slug = namn.lower().replace(" ", "")
    return {
        "company_name": namn,
        "website": f"https://{slug}.se",
        "orgnr": "556824-9022",
        "ort": "Göteborg",
        "postnr": "421 32",
        "contact_email": f"info@{slug}.se",
        "contact_level": "role_address",
        "anstallda": None,
    }


def _installera(monkeypatch, pool: list[dict], bra: set[str]) -> None:
    async def _hitta(icp, antal, *, uteslut_namn=None, profil=None, ring=0):
        uteslut = {n.casefold() for n in (uteslut_namn or set())}
        return [b for b in pool if b["company_name"].casefold() not in uteslut][:antal]

    async def _research(storage, tenant_id, *, prospect_id, **_k):
        rad = await storage.get_prospect(tenant_id, prospect_id)
        ok = rad["company_name"] in bra
        return {
            "qualified": ok,
            "icp_fit": 0.85 if ok else 0.3,
            "score_total": 85 if ok else 30,
            "disqualifiers": [] if ok else ["Storlek: 700 anställda enligt källmaterialet"],
            "stopped_early": None if ok else "ej_kvalificerad",
        }

    async def _utkast(*_a, **_k):
        return {"subject": "Hej"}

    monkeypatch.setattr(korningsmodul, "hitta_bolag", _hitta)
    monkeypatch.setattr(leads_api, "_valj_leads_kedja", lambda: (_research, _utkast))


def _payload(job_id: str, mal: int) -> dict:
    return {
        "kind": "batch",
        "job_id": job_id,
        **TENANT,
        "scope": "research",
        "overrides": None,
        "is_test": True,
        "limit": mal,
        "company_names": [],
    }


async def _vanta_klar(storage: MemoryStorage, job_id: str) -> dict:
    for _ in range(200):
        rad = await storage.get_leads_korning(TENANT["tenant_id"], job_id)
        if rad and rad["korning"] and rad["korning"].get("klar"):
            return rad
        await asyncio.sleep(0.02)
    raise AssertionError(f"körningen blev aldrig klar i liggaren: {rad}")


async def test_tillstandet_overlever_att_jobbstoret_toms(monkeypatch):
    """(a) + (b)."""
    pool = [_bolag(n) for n in ("Dålig Ett", "Bra Ett", "Bra Två")]
    _installera(monkeypatch, pool, bra={"Bra Ett", "Bra Två"})
    storage = MemoryStorage()
    app_state = SimpleNamespace(jobs=MemoryJobStore(), storage=storage, leadsstrom=None)
    job_id = await app_state.jobs.create(tenant_id=TENANT["tenant_id"], status="queued")
    await storage.set_leads_job_status(TENANT["tenant_id"], job_id=job_id, status="queued", scope="batch", is_test=True)

    await leads_api._run_batch(app_state, _payload(job_id, 2))

    # (a) Motorn har startat: raden är 'processing' och bär tillståndet —
    # inte 'completed', som den gjorde när sökjobbet räknades som hela jobbet.
    rad = await storage.get_leads_korning(TENANT["tenant_id"], job_id)
    assert rad is not None and rad["korning"] is not None
    assert rad["is_test"] is True
    assert rad["korning"]["mal"] == 2
    if not rad["korning"]["klar"]:
        assert rad["status"] == "processing"

    klar = await _vanta_klar(storage, job_id)
    assert klar["status"] == "completed"
    assert klar["korning"]["levererade"] == 2
    assert klar["korning"]["slut_orsak"] == "klar"
    assert klar["korning"]["sammanfattning"]
    assert any("700 anställda" in t["skal"] for t in klar["korning"]["tratt"])

    # (b) Redis-TTL:n: jobbstoret töms helt — liggaren svarar ändå.
    app_state.jobs = MemoryJobStore()
    assert await app_state.jobs.get(job_id) is None
    kvar = await storage.get_leads_korning(TENANT["tenant_id"], job_id)
    assert kvar["korning"]["levererade"] == 2 and kvar["status"] == "completed"


async def test_ett_fel_ger_felorsak_i_klartext(monkeypatch):
    """(c): det som saknades när körningen 2026-09-30 dog utan spår."""
    _installera(monkeypatch, [], bra=set())

    async def _profil_som_faller(*_a, **_k):
        raise RuntimeError("profilen gick inte att läsa")

    monkeypatch.setattr(leads_api, "_korningens_profil", _profil_som_faller)
    storage = MemoryStorage()
    app_state = SimpleNamespace(jobs=MemoryJobStore(), storage=storage, leadsstrom=None)
    job_id = await app_state.jobs.create(tenant_id=TENANT["tenant_id"], status="queued")

    await leads_api._run_batch(app_state, _payload(job_id, 1))

    rad = await storage.get_leads_korning(TENANT["tenant_id"], job_id)
    assert rad["status"] == "failed"
    assert rad["error"], "en död körning utan felorsak är exakt felet invarianten stänger"
    # Tillståndet från starten står kvar bredvid felet (coalesce-semantiken).
    assert rad["korning"] is not None and rad["korning"]["mal"] == 1


async def test_korningslistan_bar_batch_och_lista_men_inte_prospektjobb():
    """(d)."""
    storage = MemoryStorage()
    t = TENANT["tenant_id"]
    await storage.set_leads_job_status(t, job_id="b1", status="processing", scope="batch", korning={"mal": 3})
    await storage.set_leads_job_status(t, job_id="l1", status="failed", scope="lista", error="Budgeten är slut.")
    await storage.set_leads_job_status(t, job_id="p1", status="completed", scope="research", prospect_id="x")
    await storage.set_leads_job_status("00000000-0000-0000-0000-00000000c3c3", job_id="b9", status="queued", scope="batch")

    rader = await storage.list_leads_korningar(t)
    assert [r["job_id"] for r in rader] == ["l1", "b1"]  # nyast först
    assert rader[0]["error"] == "Budgeten är slut." and rader[0]["korning"] is None
    assert rader[1]["korning"] == {"mal": 3}
    assert await storage.get_leads_korning(t, "p1") is None
    assert await storage.get_leads_korning(t, "b9") is None

    # Ett statusbyte utan tillstånd raderar inte tillståndet.
    await storage.set_leads_job_status(t, job_id="b1", status="completed", scope="batch")
    assert (await storage.get_leads_korning(t, "b1"))["korning"] == {"mal": 3}
