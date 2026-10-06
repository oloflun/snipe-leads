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
  d) körningslistan bär batch- och listrader, aldrig prospektjobben,
  e) ett barnjobb som strömmen ger upp räknas in, så körningen aldrig står
     i 'processing' för evigt (granskningsfynd 2026-10-02),
  f) ett återtag efter deploy fortsätter ur liggaren i stället för att söka
     om från början, även när jobbstoret är tomt.
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
        # Leverbart kräver sedan 2026-10-02 kontaktperson med roll (_leverbarhet).
        "contact_name": "Test Testsson",
        "contact_role": "VD",
        "anstallda": None,
    }


def _installera(monkeypatch, pool: list[dict], bra: set[str]) -> None:
    async def _hitta(icp, antal, *, uteslut_namn=None, profil=None, ring=0, listspar=None):
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
            "lagesbeskrivning": "Bolaget bygger i Göteborg och rekryterar enligt sajten." if ok else None,
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
        # En körning behöver en målgrupp att söka i (korning.har_malgrupp).
        "overrides": {"industries": ["Redovisning"]},
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


async def test_ett_uppgivet_barnjobb_laser_inte_korningen(monkeypatch):
    """(e). Strömmen ger upp ett prospektjobb (MAX_LEVERANSER): utan
    rapporten till körningen gick `pagaende` aldrig till noll."""
    _installera(monkeypatch, [], bra=set())
    storage = MemoryStorage()
    app_state = SimpleNamespace(jobs=MemoryJobStore(), storage=storage, leadsstrom=None)
    t = TENANT["tenant_id"]
    batch_id = await app_state.jobs.create(tenant_id=t, status="processing")
    prospekt = await storage.create_prospect(t, company_name="Trasiga AB", contact_name=None, contact_email=None, origin="test")
    k = korningsmodul.ny_korning(mal=1, scope="research", overrides=None, is_test=True)
    k["pagaende"] = 1
    k["jobs"] = [{"job_id": "barn-1", "prospect_id": prospekt["id"], "company_name": "Trasiga AB"}]
    await app_state.jobs.complete(batch_id, {"korning": k, "jobs": k["jobs"], "count": 1})
    await storage.set_leads_job_status(t, job_id=batch_id, status="processing", scope="batch", korning=k, is_test=True)
    await storage.set_leads_job_status(t, job_id="barn-1", status="processing", scope="research", prospect_id=prospekt["id"])

    await leads_api.ge_upp_leadsjobb(
        app_state,
        {"job_id": "barn-1", **TENANT, "kind": "research", "scope": "research",
         "prospect_id": prospekt["id"], "batch_id": batch_id},
    )

    barn = await storage.get_leads_korning(t, "barn-1")
    assert barn is None  # prospektjobb är inte körningar
    rad = await storage.get_leads_korning(t, batch_id)
    assert rad["status"] != "processing", rad
    assert rad["korning"]["klar"] is True
    assert rad["korning"]["pagaende"] == 0
    assert any("gavs upp" in x["skal"] for x in rad["korning"]["tratt"])


async def test_atertag_fortsatter_ur_liggaren_utan_jobbstore(monkeypatch):
    """(f). Deploy mitt i motorn: Redis är tom, liggaren står i 'processing'
    med tillståndet. Återtaget ska fylla på därifrån, inte köra `_run_batch`
    (= ny sökning, dubbel researchkostnad)."""
    _installera(monkeypatch, [], bra=set())

    async def _aldrig(*_a, **_k):
        raise AssertionError("_run_batch ska inte köras vid ett återtag av en pågående körning")

    monkeypatch.setattr(leads_api, "_run_batch", _aldrig)
    storage = MemoryStorage()
    app_state = SimpleNamespace(jobs=MemoryJobStore(), storage=storage, leadsstrom=None)
    t = TENANT["tenant_id"]
    k = korningsmodul.ny_korning(
        mal=1, scope="research", overrides={"industries": ["Redovisning"]}, is_test=True
    )
    await storage.set_leads_job_status(t, job_id="b-deploy", status="processing", scope="batch", korning=k, is_test=True)
    assert await app_state.jobs.get("b-deploy") is None

    await leads_api.hantera_leads_jobb(app_state, _payload("b-deploy", 1))

    rad = await storage.get_leads_korning(t, "b-deploy")
    assert rad["korning"]["klar"] is True and rad["status"] == "completed"
    assert rad["korning"]["slut_orsak"] == "slut_pa_kandidater"


async def test_kandidatpoolen_lamnar_aldrig_apiet():
    """Kandidaterna (namn, roll, telefon ur registret) är motorns arbetsminne."""
    rad = {"job_id": "x", "korning": {"mal": 1, "kandidater": [{"company_name": "Alfa AB"}], "jobs": []}}
    ut = leads_api._utan_kandidater(rad)
    assert "kandidater" not in ut["korning"] and ut["korning"]["mal"] == 1
    assert "kandidater" in rad["korning"], "originalet muteras inte"
