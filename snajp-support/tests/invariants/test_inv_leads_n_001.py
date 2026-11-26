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
from tests.orgnr_fixtur import orgnr_for
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
        "orgnr": orgnr_for(namn),
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

    async def _hitta(icp, antal, *, uteslut_namn=None, profil=None, ring=0, listspar=None, bortval=None, bred=False):
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
            # En körning behöver en målgrupp att söka i (korning.har_malgrupp).
            "overrides": {"industries": ["Redovisning"]},
            "is_test": True,
            "limit": mal,
            "company_names": [],
        },
    )
    for _ in range(200):
        post = await app_state.jobs.get(job_id)
        k = (post.get("result") or {}).get("korning") or {}
        # Klar, eller vilande under målet (Antons regel 2026-11-24).
        if k.get("klar") or (k.get("vilande") and not k.get("pagaende")):
            return k
        await asyncio.sleep(0.02)
    raise AssertionError(f"körningen blev aldrig klar eller vilande: {k}")


async def test_n_leverbara_trots_underkanda_kandidater(monkeypatch):
    pool = [_bolag(n) for n in ("Dålig Ett", "Bra Ett", "Dålig Två", "Bra Två", "Bra Tre")]
    _installera(monkeypatch, pool, bra={"Bra Ett", "Bra Två", "Bra Tre"})
    k = await _kor(2)
    assert k["levererade"] == 2
    assert k["slut_orsak"] == "klar"
    assert any("700 anställda" in t["skal"] for t in k["tratt"])
    assert k["sammanfattning"]


async def test_slut_pa_kandidater_ger_en_vilande_korning(monkeypatch):
    """Var test_slut_pa_kandidater_namnger_flaskhalsen. Antons regel
    2026-11-24: en Iris-körning blir aldrig klar under målet. Är målgruppen
    tom (TOMMA_RUNDOR) och går inget bortval att fylla på med (här saknar de
    lägesbeskrivning) vilar körningen, med skälet."""
    pool = [_bolag(n) for n in ("Dålig Ett", "Dålig Två")]
    rundor = _installera(monkeypatch, pool, bra=set())
    k = await _kor(2)
    assert k["levererade"] == 0
    assert not k["klar"] and k["slut_orsak"] is None
    assert k["vilande"]["skal"] == "registret"
    assert int(k["tomma_rundor"]) >= korningsmodul.TOMMA_RUNDOR
    # Nya sökrundor kördes i nästa geo-ring innan den gav upp.
    assert rundor == list(range(len(rundor))) and len(rundor) >= 2


async def test_taket_ar_ett_larm_inte_ett_slut(monkeypatch):
    """Var test_taket_hindrar_en_skenande_korning (undersokta <= TAK_FAKTOR).
    Demon 2026-11-24: 8 av 10 med 118 undersökta, fast registret hade 1 169
    bolag kvar. Taket förlängs nu och körningen slutar först när målgruppen
    är tom (TOMMA_RUNDOR)."""
    pool = [_bolag(f"Dålig {i}") for i in range(30)]
    _installera(monkeypatch, pool, bra=set())
    k = await _kor(1)
    # Alla 30 researchades (och prövades sedan som påfyllnad): taket stoppade
    # inte. Utan ett leverbart bortval vilar körningen (2026-11-24).
    assert k["undersokta"] >= 30 > korningsmodul.TAK_FAKTOR
    assert not k["klar"] and k["vilande"]["skal"] == "registret"


async def test_en_snal_pool_fortsatter_forbi_rundtaket(monkeypatch):
    """En pool som ger färre än MAX_PER_RUNDA kandidater per runda: förr tog
    max_rundor slut långt innan registret, nu fortsätter körningen tills den
    hittat leadet (eller TOMMA_RUNDOR)."""
    pool = [_bolag(f"Dålig {i}") for i in range(20)] + [_bolag("Bra Sist")]
    rundor: list[int] = []

    async def _hitta(icp, antal, *, uteslut_namn=None, ring=0, **_k):
        rundor.append(ring)
        uteslut = {n.casefold() for n in (uteslut_namn or set())}
        return [b for b in pool if b["company_name"].casefold() not in uteslut][:2]

    _installera(monkeypatch, [], bra={"Bra Sist"})
    monkeypatch.setattr(korningsmodul, "hitta_bolag", _hitta)
    k = await _kor(1)
    assert k["levererade"] == 1 and k["slut_orsak"] == "klar", k
    assert len(rundor) > korningsmodul.max_rundor(1)
    assert k["undersokta"] > korningsmodul.TAK_FAKTOR


def test_flaskhalsen_raknar_inte_registrets_gratisbortval():
    """Demon 2026-11-24: "för stort" (621 gratis storleksbortval i registret)
    stod som strypare fast taket var det som stoppade."""
    k = korningsmodul.ny_korning(mal=2, scope="research", overrides=None, is_test=True)
    k["tratt"] = [{"namn": f"R{i}", "steg": "register", "skal": "För stort: 700 anställda"} for i in range(5)]
    k["tratt"] += [{"namn": f"J{i}", "steg": "jev", "skal": "Fel bransch: bilhandel"} for i in range(3)]
    k["tratt"].append({"namn": "X", "steg": "research", "skal": "Ingen kontaktmejl till bolaget"})
    korningsmodul.avsluta(k, "slut_pa_kandidater")
    assert k["flaskhals"] == "Ingen kontaktmejl till bolaget"
    # Ett tak som stoppade namnges.
    t = korningsmodul.ny_korning(mal=2, scope="research", overrides=None, is_test=True)
    t["tratt"] = [{"namn": "R", "steg": "register", "skal": "För stort: 700 anställda"}]
    korningsmodul.avsluta(t, "kredittak")
    assert t["flaskhals"] == "Sidtaket"
    assert "strypte mest: sidtaket" in korningsmodul.sammanfatta(t)


def test_leverbart_kraver_kontaktperson_kontaktvag_och_lagesbeskrivning():
    """Antons krav 2026-10-01, kodat i _leverbarhet (plan del C): det som
    saknas syns som skäl i tratten, aldrig som ett levererat lead."""
    from app.leads import eskalering

    regler = eskalering.normalisera({"kvalificeringstroskel": 50})
    ok = {"qualified": True, "icp_fit": 0.9, "score_total": 90, "lagesbeskrivning": "Bolaget …"}
    rad = {"contact_name": "Test Testsson", "contact_role": "VD", "contact_email": "test@alfa.se", "website": "https://alfa.se"}
    assert leads_api._leverbarhet(rad, ok, regler) is None
    # Sebbes beslut 2026-10-07: det enda kontaktkravet är en kontaktmejl till
    # bolaget. Namn och roll föredras men krävs inte; info@ duger.
    assert leads_api._leverbarhet({**rad, "contact_role": None}, ok, regler) is None
    assert leads_api._leverbarhet({**rad, "contact_name": None, "contact_email": "info@alfa.se"}, ok, regler) is None
    # En telefon ensam når inte fram med ett utkast.
    utan_mejl = {**rad, "contact_email": None, "contact_phone": "070-1"}
    assert leads_api._leverbarhet(utan_mejl, ok, regler) == "Ingen kontaktmejl till bolaget"
    # Främmande domän, privat adress eller HR-adress är ingen kontaktmejl.
    for fel in ("info@annat.se", "alfa@gmail.com", "rekrytering@alfa.se"):
        assert leads_api._leverbarhet({**rad, "contact_email": fel}, ok, regler) == "Ingen kontaktmejl till bolaget", fel
    assert leads_api._leverbarhet(rad, {**ok, "lagesbeskrivning": "  "}, regler) == "Ingen lägesbeskrivning"
    # Lägesbeskrivningen får komma från raden (sparad av researchen).
    assert leads_api._leverbarhet({**rad, "lagesbeskrivning": "Sparad."}, {**ok, "lagesbeskrivning": None}, regler) is None
    assert leads_api._leverbarhet(rad, {**ok, "qualified": False, "disqualifiers": ["För stort"]}, regler) == "För stort"


async def test_kundens_branscher_slut_breddar_i_omradet_och_levererar(monkeypatch):
    """Antons beställning 2026-10-23: leverera beställt antal. När kundens
    egna branscher är genomsökta (en tom runda) söker körningen brett i samma
    område i stället för att räkna mot slutet, och sammanfattningen säger det."""
    egna = [_bolag("Bra Ett")]
    breda = [_bolag(n) for n in ("Bra Två", "Bra Tre", "Bra Fyra")]
    anrop: list[bool] = []

    async def _hitta(icp, antal, *, uteslut_namn=None, bred=False, **_k):
        anrop.append(bred)
        uteslut = {n.casefold() for n in (uteslut_namn or set())}
        return [b for b in (breda if bred else egna) if b["company_name"].casefold() not in uteslut][:antal]

    _installera(monkeypatch, [], bra={"Bra Ett", "Bra Två", "Bra Tre", "Bra Fyra"})
    monkeypatch.setattr(korningsmodul, "hitta_bolag", _hitta)
    monkeypatch.setattr(leads_api.merinfo, "aktiv", lambda: True)
    k = await _kor(3)
    assert k["levererade"] == 3 and k["slut_orsak"] == "klar", k
    assert k["bred"] and anrop[0] is False and True in anrop
    assert "breddades" in k["sammanfattning"]


async def test_strukturvalet_foljer_korningen_till_varje_barn(monkeypatch):
    """Utkastens struktur (A/B, Sebbe 2026-11-05) står i körningens tillstånd
    och följer med varje prospektjobb motorn lägger, också påfyllningarna."""
    pool = [_bolag(n) for n in ("Bra Ett", "Bra Två", "Bra Tre")]
    _installera(monkeypatch, pool, bra={"Bra Ett", "Bra Två", "Bra Tre"})
    sedda: list[str] = []
    riktig = leads_api._lagg_prospektjobb

    async def _spion(*a, **k):
        sedda.append(k.get("struktur"))
        return await riktig(*a, **k)

    monkeypatch.setattr(leads_api, "_lagg_prospektjobb", _spion)
    app_state = SimpleNamespace(jobs=MemoryJobStore(), storage=MemoryStorage(), leadsstrom=None)
    job_id = await app_state.jobs.create(tenant_id=TENANT["tenant_id"], status="queued")
    await leads_api._run_batch(
        app_state,
        {
            "kind": "batch", "job_id": job_id, **TENANT, "scope": "research",
            "overrides": {"industries": ["Redovisning"]}, "is_test": True, "limit": 2,
            "company_names": [], "struktur": "b",
        },
    )
    for _ in range(200):
        k = ((await app_state.jobs.get(job_id)).get("result") or {}).get("korning") or {}
        if k.get("klar"):
            break
        await asyncio.sleep(0.02)
    assert k.get("struktur") == "b"
    assert sedda and set(sedda) == {"b"}
