"""INV-LEADS-N-001 — en körning levererar N leverbara leads, eller säger ärligt varför inte.

Uppmätt 2026-09-29 hos Alunix: 3 beställda leads blev 3 kandidater som Iris
själv underkände, och inga utkast. Testet kör den riktiga motorn
(`_run_batch` → `_fyll_pa` → prospektjobb → `_rapportera_till_korning`) mot
MemoryStorage med en fejkad sökning och en fejkad research — det som prövas
är räkningen, påfyllningen och slutet.
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
TENANT = {"tenant_id": "00000000-0000-0000-0000-00000000a1a1", "tenant_name": "Testbyrån"}


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


def _installera(monkeypatch, pool: list[dict], bra: set[str]) -> list[int]:
    rundor: list[int] = []

    async def _hitta(icp, antal, *, uteslut_namn=None, profil=None, ring=0):
        rundor.append(ring)
        uteslut = {n.casefold() for n in (uteslut_namn or set())}
        kvar = [b for b in pool if b["company_name"].casefold() not in uteslut]
        return kvar[:antal]

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
    return rundor


async def _kor(mal: int) -> dict:
    app_state = SimpleNamespace(jobs=MemoryJobStore(), storage=MemoryStorage(), leadsstrom=None)
    job_id = await app_state.jobs.create(tenant_id=TENANT["tenant_id"], status="queued")
    await leads_api._run_batch(
        app_state,
        {
            "kind": "batch",
            "job_id": job_id,
            **TENANT,
            "scope": "research",
            "overrides": None,
            "is_test": True,
            "limit": mal,
            "company_names": [],
        },
    )
    for _ in range(200):
        post = await app_state.jobs.get(job_id)
        k = (post.get("result") or {}).get("korning") or {}
        if k.get("klar"):
            return k
        await asyncio.sleep(0.02)
    raise AssertionError(f"körningen blev aldrig klar: {k}")


async def test_n_leverbara_trots_underkanda_kandidater(monkeypatch):
    pool = [_bolag(n) for n in ("Dålig Ett", "Bra Ett", "Dålig Två", "Bra Två", "Bra Tre")]
    _installera(monkeypatch, pool, bra={"Bra Ett", "Bra Två", "Bra Tre"})
    k = await _kor(2)
    assert k["levererade"] == 2
    assert k["slut_orsak"] == "klar"
    assert any("700 anställda" in t["skal"] for t in k["tratt"])
    assert k["sammanfattning"]


async def test_slut_pa_kandidater_namnger_flaskhalsen(monkeypatch):
    pool = [_bolag(n) for n in ("Dålig Ett", "Dålig Två")]
    rundor = _installera(monkeypatch, pool, bra=set())
    k = await _kor(2)
    assert k["levererade"] == 0
    assert k["klar"] and k["slut_orsak"] in ("slut_pa_kandidater", "tak")
    assert k["flaskhals"] == "Storlek"
    # Nya sökrundor kördes i nästa geo-ring innan den gav upp.
    assert rundor == list(range(len(rundor))) and len(rundor) >= 2


async def test_taket_hindrar_en_skenande_korning(monkeypatch):
    pool = [_bolag(f"Dålig {i}") for i in range(30)]
    _installera(monkeypatch, pool, bra=set())
    k = await _kor(1)
    assert k["undersokta"] <= korningsmodul.TAK_FAKTOR * 1
    assert k["klar"]


def test_leverbart_kraver_kontaktperson_kontaktvag_och_lagesbeskrivning():
    """Antons krav 2026-10-01, kodat i _leverbarhet (plan del C): det som
    saknas syns som skäl i tratten, aldrig som ett levererat lead."""
    from app.leads import eskalering

    regler = eskalering.normalisera({"kvalificeringstroskel": 50})
    ok = {"qualified": True, "icp_fit": 0.9, "score_total": 90, "lagesbeskrivning": "Bolaget …"}
    rad = {"contact_name": "Test Testsson", "contact_role": "VD", "contact_phone": "070-1", "website": "https://alfa.se"}
    assert leads_api._leverbarhet(rad, ok, regler) is None
    assert leads_api._leverbarhet({**rad, "contact_role": None}, ok, regler) == "Ingen kontaktperson med roll"
    assert leads_api._leverbarhet({**rad, "contact_phone": None}, ok, regler).startswith("Ingen kontaktväg")
    # Arbetsmejl räcker som kontaktväg när telefon saknas.
    assert leads_api._leverbarhet({**rad, "contact_phone": None, "contact_email": "vd@alfa.se"}, ok, regler) is None
    assert leads_api._leverbarhet(rad, {**ok, "lagesbeskrivning": "  "}, regler) == "Ingen lägesbeskrivning"
    # Lägesbeskrivningen får komma från raden (sparad av researchen).
    assert leads_api._leverbarhet({**rad, "lagesbeskrivning": "Sparad."}, {**ok, "lagesbeskrivning": None}, regler) is None
    assert leads_api._leverbarhet(rad, {**ok, "qualified": False, "disqualifiers": ["För stort"]}, regler) == "För stort"
